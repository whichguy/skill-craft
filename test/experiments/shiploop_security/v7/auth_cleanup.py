"""Remove the Codex auth link in a leased, private V7 output after its processes end."""
from contextlib import ExitStack
import os
import stat


def cleanup_auth_link(out, *, drained):
    """Return a status without recording paths, link targets, or exception text."""
    if not drained:
        return {"status": "not-drained"}
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    try:
        with ExitStack() as stack:
            fd = os.open(out, flags)
            stack.callback(os.close, fd)
            for name in ("home", ".codex"):
                if not stat.S_ISDIR(os.stat(name, dir_fd=fd, follow_symlinks=False).st_mode):
                    return {"status": "refused", "reason": "unexpected-parent"}
                fd = os.open(name, flags, dir_fd=fd)
                stack.callback(os.close, fd)
            if not stat.S_ISLNK(os.stat("auth.json", dir_fd=fd, follow_symlinks=False).st_mode):
                return {"status": "refused", "reason": "unexpected-entry"}
            os.unlink("auth.json", dir_fd=fd)
    except FileNotFoundError:
        return {"status": "absent"}
    except OSError:
        return {"status": "refused", "reason": "filesystem-error"}
    return {"status": "removed"}
