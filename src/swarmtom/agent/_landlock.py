"""Linux child-only filesystem policy, based on the kernel's Landlock userspace API.

https://docs.kernel.org/userspace-api/landlock.html
Requires ABI >= 3 (including cross-directory rename and truncate restrictions).
There is deliberately no fallback to a Python-only open() guard.
"""


def restrict_filesystem(workspace, read_paths):
    import ctypes
    import os
    import platform

    if platform.machine() not in ("x86_64", "aarch64"):
        raise RuntimeError("Landlock syscall numbers are only configured for x86_64/aarch64")
    libc = ctypes.CDLL(None, use_errno=True)
    syscall = libc.syscall
    syscall.restype = ctypes.c_long

    def call(number, *args):
        result = syscall(number, *args)
        if result < 0:
            raise OSError(ctypes.get_errno(), "Landlock filesystem isolation failed")
        return result

    abi = call(444, ctypes.c_void_p(), 0, 1)  # landlock_create_ruleset(..., VERSION)
    if abi < 3:
        raise RuntimeError("Filesystem isolation requires Landlock ABI >= 3; enable it on the host kernel")

    class Ruleset(ctypes.Structure):
        _fields_ = [("handled_access_fs", ctypes.c_uint64)]

    class Beneath(ctypes.Structure):
        _pack_ = 1
        _fields_ = [("allowed_access", ctypes.c_uint64), ("parent_fd", ctypes.c_int32)]

    # ABI 3 filesystem operations: execute/read/write/create/remove/rename/truncate.
    handled = (1 << 15) - 1
    ruleset = Ruleset(handled)
    fd = call(444, ctypes.byref(ruleset), ctypes.sizeof(ruleset), 0)
    try:
        for path, access in [(p, 1 | 4 | 8) for p in read_paths] + [(workspace, handled)]:
            if not os.path.exists(path):
                continue
            if not os.path.isdir(path):
                access &= 1 | 2 | 4 | (1 << 14)
            parent = os.open(path, os.O_PATH | os.O_CLOEXEC)
            try:
                rule = Beneath(access, parent)
                call(445, fd, 1, ctypes.byref(rule), 0)  # landlock_add_rule(PATH_BENEATH)
            finally:
                os.close(parent)
        if libc.prctl(38, 1, 0, 0, 0):  # PR_SET_NO_NEW_PRIVS
            raise OSError(ctypes.get_errno(), "cannot set no_new_privs")
        call(446, fd, 0)  # landlock_restrict_self
    finally:
        os.close(fd)
