//! Linux host validation helper; not a production Atto runtime.
use std::io::{self, Read};
use std::os::fd::AsRawFd;
use std::os::unix::process::CommandExt;
use std::process::{Command, ExitStatus, Stdio};
use std::time::{Duration, Instant};

#[derive(Debug, PartialEq, Eq)]
pub enum Failure { InvalidLimits, Spawn, Pipe, Timeout, OutputBudget, OrphanedPipes, InvalidUtf8, Wait }
#[derive(Debug)]
pub struct Captured { pub status: ExitStatus, pub stdout: String, pub stderr: String }

// Linux-only ABI; no external dependencies.
unsafe extern "C" {
    fn fcntl(fd: i32, cmd: i32, ...) -> i32;
    fn kill(pid: i32, sig: i32) -> i32;
}
fn nonblocking(fd: i32) -> Result<(), Failure> {
    let flags = unsafe { fcntl(fd, 3) };
    if flags < 0 || unsafe { fcntl(fd, 4, flags | 0o4000) } < 0 { return Err(Failure::Pipe); }
    Ok(())
}
fn drain(pipe: &mut impl Read, dst: &mut Vec<u8>, other: usize, max: usize, eof: &mut bool) -> Result<(), Failure> {
    if *eof { return Ok(()); }
    let mut buf = [0_u8; 8192];
    match pipe.read(&mut buf) {
        Ok(0) => *eof = true,
        Ok(n) => {
            if n > max.saturating_sub(dst.len().saturating_add(other)) { return Err(Failure::OutputBudget); }
            dst.extend_from_slice(&buf[..n]);
        }
        Err(e) if matches!(e.kind(), io::ErrorKind::WouldBlock | io::ErrorKind::Interrupted) => (),
        Err(_) => return Err(Failure::Pipe),
    }
    Ok(())
}
pub fn run_bounded(cmd: &mut Command, timeout: Duration, max: usize) -> Result<Captured, Failure> {
    if timeout.is_zero() || max == 0 { return Err(Failure::InvalidLimits); }
    let deadline = Instant::now().checked_add(timeout).ok_or(Failure::InvalidLimits)?;
    let mut child = cmd.stdin(Stdio::null()).stdout(Stdio::piped()).stderr(Stdio::piped())
        .process_group(0).spawn().map_err(|_| Failure::Spawn)?;
    let pgid = child.id() as i32;
    let result = (|| {
        let mut stdout = child.stdout.take().ok_or(Failure::Pipe)?;
        let mut stderr = child.stderr.take().ok_or(Failure::Pipe)?;
        nonblocking(stdout.as_raw_fd())?;
        nonblocking(stderr.as_raw_fd())?;
        let (mut out, mut err) = (Vec::new(), Vec::new());
        let (mut out_eof, mut err_eof) = (false, false);
        let mut exited = None;
        loop {
            if Instant::now() >= deadline { return Err(Failure::Timeout); }
            // Alternate streams, enforcing one aggregate byte budget.
            drain(&mut stdout, &mut out, err.len(), max, &mut out_eof)?;
            drain(&mut stderr, &mut err, out.len(), max, &mut err_eof)?;
            if exited.is_none() {
                if let Some(status) = child.try_wait().map_err(|_| Failure::Wait)? {
                    exited = Some((status, Instant::now()));
                }
            }
            if let Some((status, at)) = exited {
                if out_eof && err_eof {
                    return Ok(Captured {
                        status,
                        stdout: String::from_utf8(out).map_err(|_| Failure::InvalidUtf8)?,
                        stderr: String::from_utf8(err).map_err(|_| Failure::InvalidUtf8)?,
                    });
                }
                if at.elapsed() >= Duration::from_secs(1) { return Err(Failure::OrphanedPipes); }
            }
            std::thread::sleep(Duration::from_millis(2));
        }
    })();
    if result.is_err() {
        // Process-group cleanup, including descendants retaining pipes.
        // Not a sandbox against a deliberately escaping setsid process.
        unsafe { kill(-pgid, 9); }
        let _ = child.kill();
        let _ = child.wait();
    }
    result
}
