#![cfg(target_os = "linux")]
#[path = "support/bounded_process.rs"]
mod bounded_process;
use bounded_process::{run_bounded, Failure};
use std::{fs, process::Command, time::Duration};

fn sh(s: &str, ms: u64, max: usize) -> Result<bounded_process::Captured, Failure> {
    run_bounded(Command::new("bash").arg("-c").arg(s), Duration::from_millis(ms), max)
}
#[test]
fn distinct_streams_and_nonzero_exit() {
    let r = sh("printf 'out\\n'; printf 'err\\n' >&2; exit 23", 5000, 8).unwrap();
    assert_eq!(r.status.code(), Some(23));
    assert_eq!(r.stdout, "out\n");
    assert_eq!(r.stderr, "err\n");
}
#[test]
fn aggregate_exact_limit_and_overflow() {
    let r = sh("printf '%02048d' 0; printf '%02048d' 0 >&2", 5000, 4096).unwrap();
    assert_eq!((r.stdout.len(), r.stderr.len()), (2048, 2048));
    assert_eq!(sh("printf '%02048d' 0; printf '%02048d' 0 >&2", 5000, 4095).unwrap_err(), Failure::OutputBudget);
    assert_eq!(sh("printf zz >&2", 5000, 1).unwrap_err(), Failure::OutputBudget);
    assert_eq!(sh("printf z >&2", 5000, 1).unwrap().stderr, "z");
    assert_eq!(sh(":", 5000, 1).unwrap().stdout, "");
}
#[test]
fn oversized_stream_is_terminated() {
    assert_eq!(sh("exec yes X", 5000, 32768).unwrap_err(), Failure::OutputBudget);
}
#[test]
fn strict_utf8_on_both_streams() {
    assert_eq!(sh("printf '\\377'", 5000, 8).unwrap_err(), Failure::InvalidUtf8);
    assert_eq!(sh("printf '\\377' >&2", 5000, 8).unwrap_err(), Failure::InvalidUtf8);
}
#[test]
fn invalid_limits_precede_spawn() {
    let mut absent = Command::new("/no-such-atto-test-executable");
    assert_eq!(run_bounded(&mut absent, Duration::ZERO, 1).unwrap_err(), Failure::InvalidLimits);
    assert_eq!(run_bounded(&mut absent, Duration::from_secs(1), 0).unwrap_err(), Failure::InvalidLimits);
    assert_eq!(run_bounded(&mut absent, Duration::from_secs(1), 1).unwrap_err(), Failure::Spawn);
}
#[test]
fn timeout_is_not_success() {
    assert_eq!(sh("exec sleep 30", 100, 8).unwrap_err(), Failure::Timeout);
}
fn descendant_case(orphan: bool) {
    let path = std::env::temp_dir().join(format!("atto-bounded-{}-{}", std::process::id(), orphan));
    let _ = fs::remove_file(&path);
    let script = if orphan {
        "sleep 30 & printf '%s' \"$!\" > \"$1\"; exit 0"
    } else {
        "sleep 30 & printf '%s' \"$!\" > \"$1\"; wait"
    };
    let outcome = run_bounded(Command::new("bash").arg("-c").arg(script)
        .arg("bounded").arg(&path), Duration::from_secs(if orphan {5} else {2}), 1024);
    assert_eq!(outcome.unwrap_err(), if orphan {Failure::OrphanedPipes} else {Failure::Timeout});
    let pid = fs::read_to_string(&path).expect("child was spawned");
    fs::remove_file(path).unwrap();
    let stat = format!("/proc/{}/stat", pid.trim());
    for _ in 0..100 {
        match fs::read_to_string(&stat) {
            Err(e) if e.kind() == std::io::ErrorKind::NotFound => return,
            Ok(s) if matches!(s.rsplit_once(") ").and_then(|(_, r)| r.chars().next()), Some('Z' | 'X')) => return,
            _ => std::thread::sleep(Duration::from_millis(10)),
        }
    }
    panic!("descendant remains running: {pid}");
}
#[test]
fn timeout_retires_descendants() { descendant_case(false); }
#[test]
fn orphaned_pipe_retires_descendants() { descendant_case(true); }
