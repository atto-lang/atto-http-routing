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
];

fn root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
}

fn check_language_policy(dir: &Path) {
    for item in fs::read_dir(dir).expect("read project directory") {
        let item = item.expect("read entry");
        let path = item.path();
        let name = item.file_name();
        if path.is_dir() {
            assert_ne!(name.as_os_str(), OsStr::new("__pycache__"),
                "Python cache directory forbidden: {}", path.display());
            if name.as_os_str() != OsStr::new(".git")
                && name.as_os_str() != OsStr::new("target")
            {
                check_language_policy(&path);
            }
        } else {
            let ext = path.extension().and_then(OsStr::to_str).unwrap_or("");
            assert!(!matches!(ext, "py" | "pyc" | "pyo" | "pyd"),
                "Python file forbidden: {}", path.display());
        }
    }
}

#[test]
fn rejects_python_source_and_tests() {
    check_language_policy(&root());
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
    for guest in GUESTS {
        let source = root().join(format!("tests/{guest}.atto"));
        let golden = fs::read(root().join(format!("tests/{guest}.expected")))
            .expect("read golden file");
        execute(&compiler, &source, &["--check", "--platform=server"]);
        let stdout = execute(&compiler, &source, &["--platform=server"]);
        assert_eq!(stdout, golden, "native guest output mismatch for {guest}");
    }
}
