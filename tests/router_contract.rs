//! Rust-only harness for native Atto routing fixtures.
//! Passing host tests DOES NOT establish executed guest semantics.

use std::ffi::OsStr;
use std::fs;
use std::path::{Path, PathBuf};
use std::process::Command;

const GUESTS: &[&str] = &[
    "guest_router_adversarial",
    "guest_method_tokens",
    "guest_snapshot_isolation",
    "guest_capture_precedence",
    "guest_route_name_validation",
];

fn root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
}

fn check_language_policy(dir: &Path) {
    for item in fs::read_dir(dir).expect("read project directory") {
        let item = item.expect("read entry");
        let path = item.path();
        let name = item.file_name();
        let metadata = fs::symlink_metadata(&path).expect("inspect entry metadata");
        assert!(!metadata.file_type().is_symlink(),
            "symlinks are prohibited in the source/test tree: {}", path.display());
        if metadata.is_dir() {
            assert_ne!(name.as_os_str(), OsStr::new("__pycache__"),
                "Python cache directory forbidden: {}", path.display());
            if name.as_os_str() != OsStr::new(".git")
                && name.as_os_str() != OsStr::new("target")
            {
                check_language_policy(&path);
            }
        } else {
            assert!(metadata.is_file(), "nonregular file forbidden: {}", path.display());
            let file_name = name.to_string_lossy().to_ascii_lowercase();
            let ext = path.extension().and_then(OsStr::to_str)
                .unwrap_or("").to_ascii_lowercase();
            assert!(!matches!(ext.as_str(), "py" | "pyc" | "pyo" | "pyd")
                && !matches!(file_name.as_str(),
                    "requirements.txt" | "pyproject.toml" | "pipfile" | "pipfile.lock"
                    | "poetry.lock" | ".python-version"),
                "Python file/dependency forbidden: {}", path.display());
            if matches!(ext.as_str(), "yml" | "yaml" | "sh" | "bash") {
                let content = fs::read_to_string(&path).expect("read workflow/script");
                let normalized = content.to_ascii_lowercase();
                for forbidden in ["python3 ", "python ", "pytest", "pip install"] {
                    assert!(!normalized.contains(forbidden),
                        "Python execution in workflow/script forbidden: {}", path.display());
                }
            }
        }
    }
}

#[test]
fn rejects_python_source_and_tests() {
    check_language_policy(&root());
}

#[test]
fn string_keys_use_atto_value_equality_not_identity() {
    let source = fs::read_to_string(root().join("src/http_routing.atto"))
        .expect("missing native Atto routing source");
    for required in [
        "previous.value eq segment.value",
        "self.static_names.get(index) eq literal_value",
        "self.static_literals.get(edge_index) eq segment",
        "self.targets_value.get(index).method eq method_value",
        "endpoint.target_at(index).method eq method_value",
        "method_value eq \"HEAD\"",
        "method_value eq \"OPTIONS\"",
        "current.param_name neq segment.value",
        "actual neq segment.value",
        "segment.value eq name",
        "decision.route_template neq endpoint.template()",
        "target.operation_id neq decision.operation_id",
    ] {
        assert!(source.contains(required), "missing Atto string value comparison: {required}");
    }
    for prohibited in [
        ".value == ", ".value != ", ".method == ", ".method != ",
        ".param_name == ", ".param_name != ", ".wildcard_name == ",
        ".wildcard_name != ", "method_value == ", "method_value != ",
        "actual == ", "actual != ", "segment == \".\"",
        "segment == \"..\"",
    ] {
        assert!(!source.contains(prohibited),
            "string identity operator used where value equality is required: {prohibited}");
    }
}

#[test]
fn native_router_is_atto_not_a_host_reference() {
    let path = root().join("src/http_routing.atto");
    let source = fs::read_to_string(path).expect("missing native Atto routing implementation");
    assert!(source.contains("define module http_routing as"));
    for contract in ["request_path_checked", "pub fnc builder()", "capture_one", "is_method_not_allowed"] {
        assert!(source.contains(contract), "missing native contract: {contract}");
    }
}

#[test]
fn route_registration_and_method_resolution_fail_closed_in_atto_source() {
    let source = fs::read_to_string(root().join("src/http_routing.atto"))
        .expect("missing native Atto router");
    for required in [
        "segment.value.starts_with(first)",
        "remaining = remaining.replace_literal(allowed, \"\")",
        "if !starts_lowercase; then",
        "if remaining neq \"\"; then",
        "pub is_invalid_method() -> bool",
        "if !self.canonical_method(method_value); then",
        "return new Decision(5, -1, -1, -1, -1, -1",
        "if segments.size > 128; then",
    ] {
        assert!(source.contains(required),
            "missing production .atto admission guard: {required}");
    }
    assert_eq!(source.matches("canonical_method(String method_value) -> bool").count(), 2,
        "registration-time and request-time method validation must both be present");
    let fixture = fs::read_to_string(root().join("tests/guest_route_name_validation.atto"))
        .expect("missing actual Atto guest negative fixture");
    for case in ["param(\"Bad\")", "param(\"9id\")", "param(\"_id\")",
        "param(\"user-id\")", "param(\"café\")", "wildcard(\"Bad\")",
        "is_invalid_method()", "builder.build().route_count() == 1",
        "request_path_checked(segments).is_err()",
        "request_path_checked(arr[\"users\", \"..\"]).is_err()"] {
        assert!(fixture.contains(case), "guest fixture lacks case: {case}");
    }
}

#[test]
fn registration_and_request_method_validators_do_not_drift() {
    let source = fs::read_to_string(root().join("src/http_routing.atto"))
        .expect("read Atto router");
    let methods: Vec<&str> = source
        .split("canonical_method(String method_value) -> bool {")
        .skip(1)
        .map(|body| body.split("\n    }").next().expect("terminated method validator"))
        .collect();
    assert_eq!(methods.len(), 2, "expected registration and request validators");
    assert_eq!(methods[0], methods[1],
        "HTTP method allowed-character sets must agree at both boundaries");
}

#[test]
fn route_security_guest_golden_covers_every_assertion() {
    let source = fs::read_to_string(root().join("tests/guest_route_name_validation.atto"))
        .expect("missing Atto hardening guest");
    let golden = fs::read_to_string(root().join("tests/guest_route_name_validation.expected"))
        .expect("missing Atto hardening golden");
    let cases = source.matches("stdio.println(").count();
    let lines: Vec<&str> = golden.lines().collect();
    assert!(cases >= 19, "Atto guest negative cases were dropped");
    assert_eq!(cases, lines.len(), "guest assertion count and golden output disagree");
    assert!(lines.iter().all(|line| *line == "true"),
        "negative guest fixture must print true for every admitted assertion");
}

#[test]
fn native_guest_fixtures_are_nonempty_and_paired() {
    for guest in GUESTS {
        let source = root().join(format!("tests/{guest}.atto"));
        let golden = root().join(format!("tests/{guest}.expected"));
        for file in [&source, &golden] {
            let metadata = fs::symlink_metadata(file).expect("missing fixture/golden");
            assert!(metadata.file_type().is_file() && !metadata.file_type().is_symlink(),
                "fixture must be regular file, not symlink: {}", file.display());
            assert!(metadata.len() > 0, "empty guest fixture or golden: {}", file.display());
        }
        let content = fs::read_to_string(source).expect("read guest fixture");
        assert!(content.contains("../src/http_routing"),
            "{guest} fails to import native Atto routing module");
    }
}

fn execute(compiler: &OsStr, source: &Path, args: &[&str]) -> Vec<u8> {
    let result = Command::new(compiler)
        .args(args)
        .arg(source)
        .current_dir(root())
        .output()
        .expect("failed to start Atto compiler");
    assert!(result.status.success(),
        "guest compiler failed for {} {:?}: {}",
        source.display(), args, String::from_utf8_lossy(&result.stderr));
    result.stdout
}

#[test]
#[ignore = "requires compatible ATTO_COMPILER and executes real native Atto fixtures"]
fn run_native_atto_guest_suite() {
    let compiler = std::env::var_os("ATTO_COMPILER")
        .expect("ATTO_COMPILER must name a compatible executable compiler");
    let source_dir = std::env::var_os("ATTO_COMPILER_SOURCE_DIR")
        .expect("ATTO_COMPILER_SOURCE_DIR must point to the exact source checkout");
    let expected = std::env::var("ATTO_COMPILER_SHA")
        .expect("ATTO_COMPILER_SHA must be a pinned 40-character Git commit");
    assert!(expected.len() == 40
        && expected.bytes().all(|b| b.is_ascii_digit() || (b'a'..=b'f').contains(&b)),
        "ATTO_COMPILER_SHA must be a full lowercase Git SHA");
    let check_git = |args: &[&str]| {
        let output = Command::new("git").arg("-C").arg(&source_dir).args(args)
            .output().expect("inspect pinned compiler checkout");
        assert!(output.status.success(),
            "git checkout inspection failed: {}", String::from_utf8_lossy(&output.stderr));
        String::from_utf8(output.stdout).expect("git output was not UTF-8")
    };
    let actual = check_git(&["rev-parse", "HEAD"]);
    assert_eq!(actual.trim(), expected, "compiler source commit differs from pin");
    assert!(check_git(&["status", "--porcelain", "--untracked-files=all"]).trim().is_empty(),
        "compiler source checkout is dirty; guest proof is not attributable");
    for guest in GUESTS {
        let source = root().join(format!("tests/{guest}.atto"));
        let golden = fs::read(root().join(format!("tests/{guest}.expected")))
            .expect("read golden file");
        execute(&compiler, &source, &["--check", "--platform=server"]);
        let stdout = execute(&compiler, &source, &["--platform=server"]);
        assert_eq!(stdout, golden, "native guest output mismatch for {guest}");
    }
}
