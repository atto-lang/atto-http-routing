"""Bound captured guest output and kill its entire subprocess group on failure."""
import os
import signal
import subprocess
import threading


def run_bounded(argv, timeout=30, max_bytes=1024 * 1024):
    if timeout <= 0 or max_bytes <= 0:
        raise ValueError('positive timeout and output budget required')
    # Isolate the compiler/guest from the CI job's own process group. A guest
    # must not keep a compiler subprocess alive after its parent exits.
    process = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               start_new_session=True)
    chunks = [bytearray(), bytearray()]
    lock = threading.Lock()
    exceeded = threading.Event()
    total = 0

    def kill_group():
        try:
            os.killpg(process.pid, signal.SIGKILL)
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
                    over_budget = total > max_bytes
                    if over_budget:
                        exceeded.set()
                if over_budget:
                    kill_group()
                    break
        finally:
            pipe.close()

    readers = [threading.Thread(target=drain, args=(pipe, i), daemon=True)
               for i, pipe in enumerate((process.stdout, process.stderr))]
    for reader in readers:
        reader.start()
    timed_out = False
    try:
        process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        kill_group()
        process.wait()
    finally:
        for reader in readers:
            reader.join(timeout=1)
    pipes_open = any(reader.is_alive() for reader in readers)
    if pipes_open:
        # If the compiler exited but left a child holding stdout/stderr open,
        # stop that entire group rather than leaking the descendant.
        kill_group()
        for reader in readers:
            reader.join(timeout=1)
    if timed_out:
        raise subprocess.TimeoutExpired(argv, timeout)
    if pipes_open:
        raise RuntimeError('compiler output pipes remained open after process exit')
    if exceeded.is_set():
        raise RuntimeError('compiler output budget exceeded')
    return subprocess.CompletedProcess(argv, process.returncode,
                                       chunks[0].decode('utf-8'), chunks[1].decode('utf-8'))
