"""单机协作写锁；共享盘须验证 flock。 / Local writer lock; shared disks require flock qualification."""

from contextlib import contextmanager
import os
from pathlib import Path
import threading

_guard = threading.RLock()
_held = {}


@contextmanager
def writer_lock(root):
    """同进程可重入，跨进程互斥。 / Reentrant locally, exclusive across processes."""
    import fcntl

    path = Path(root).resolve() / ".writer.lock"
    key = (os.getpid(), str(path))
    with _guard:
        if key in _held:
            yield
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a+b") as handle:
            fcntl.flock(handle, fcntl.LOCK_EX)
            _held[key] = handle
            try:
                yield
            finally:
                del _held[key]
                fcntl.flock(handle, fcntl.LOCK_UN)


def serialized(method):
    """锁定整个对象操作。 / Lock the complete object operation."""
    from functools import wraps

    @wraps(method)
    def call(self, *args, **kwargs):
        root = self.paths.root if hasattr(self, "paths") else self.path.parent
        with writer_lock(root):
            manager = getattr(self, "manager", self)
            if getattr(manager, "_state", None) is not None and manager.paths.state.exists():
                from .atomic_io import read_json
                if read_json(manager.paths.state) != manager._state:
                    from .session import SessionError
                    raise SessionError("concurrent state change; reload before mutation")
            return method(self, *args, **kwargs)
    return call
