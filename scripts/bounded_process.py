"""Bound captured compiler output while the process is running."""
import os
import signal
import subprocess
import threading


def run_bounded(argv, timeout=30, max_bytes=1024 * 1024):
    if timeout <= 0 or max_bytes <= 0:
        raise ValueError('positive timeout and output budget required')
    # POSIX: isolate the compiler process group so its subprocesses cannot
    # retain output pipes or continue running after cancellation.
    isolated = os.name == 'posix'
    process = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               start_new_session=isolated)
    chunks = [bytearray(), bytearray()]
    lock = threading.Lock()
    exceeded = threading.Event()
    total = 0

    def stop():
        try:
            if isolated:
                os.killpg(process.pid, signal.SIGKILL)
            else:
                process.kill()
        except ProcessLookupError:
            pass

    def drain(pipe, slot):
        nonlocal total
        try:
            while True:
                block = pipe.read(8192)
                if not block:
                    break
                with lock:
                    remaining = max_bytes - total
                    chunks[slot].extend(block[:max(0, remaining)])
                    total += len(block)
                    if total > max_bytes:
                        exceeded.set()
                        stop()
        finally:
            pipe.close()

    readers = [threading.Thread(target=drain, args=(pipe, i), daemon=True)
               for i, pipe in enumerate((process.stdout, process.stderr))]
    for reader in readers:
        reader.start()
    try:
        process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        stop()
        process.wait()
        raise
    finally:
        for reader in readers:
            reader.join(timeout=1)
    orphaned_pipes = any(reader.is_alive() for reader in readers)
    if orphaned_pipes:
        stop()
        for reader in readers:
            reader.join(timeout=1)
        raise RuntimeError('compiler output pipes remained open after process exit')
    if exceeded.is_set():
        raise RuntimeError('compiler output budget exceeded')
    return subprocess.CompletedProcess(argv, process.returncode,
                                       chunks[0].decode('utf-8'), chunks[1].decode('utf-8'))
