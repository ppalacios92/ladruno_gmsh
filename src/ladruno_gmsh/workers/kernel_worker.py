"""QThread that hosts the gmsh context and processes commands serially."""
from __future__ import annotations

import queue
import traceback
from typing import Any, Callable, Optional

from .messages import Command, Result


def _require_qt():
    try:
        from qtpy import QtCore
    except ImportError as exc:
        raise ImportError(
            "The worker requires PyQt5/qtpy. "
            'Install with: pip install "ladruno_gmsh[viewer]"'
        ) from exc
    return QtCore


class KernelWorker:
    """Adapter that runs callables on a :class:`QtCore.QThread`.

    Although the worker exists mainly to isolate the UI thread from
    long operations, it is conceptually agnostic of its contents: any
    ``Callable[[dict], Any]`` registered with :meth:`register` is
    available under a ``kind`` and invoked from the worker thread when
    a :class:`Command` arrives.

    Expected usage:

    1. ``worker = KernelWorker()``
    2. ``worker.register("heal", lambda payload: session.heal(**payload))``
    3. ``worker.start()``
    4. ``worker.submit(Command(kind="heal", payload={...}))``
    5. Connect ``worker.resultReady`` to the slot that updates the UI.
    """

    def __init__(self) -> None:
        QtCore = _require_qt()
        self._QtCore = QtCore

        self._handlers: dict[str, Callable[[dict[str, Any]], Any]] = {}
        self._queue: "queue.Queue[Optional[Command]]" = queue.Queue()

        class _Bridge(QtCore.QObject):
            resultReady = QtCore.Signal(object)
        self._bridge = _Bridge()
        self.resultReady = self._bridge.resultReady

        self._thread = QtCore.QThread()
        self._thread.run = self._run     # type: ignore[assignment]
        self._stopped = False

    def register(self, kind: str,
                 handler: Callable[[dict[str, Any]], Any]) -> None:
        self._handlers[kind] = handler

    def start(self) -> None:
        self._thread.start()

    def stop(self, *, wait: bool = True) -> None:
        if self._stopped:
            return
        self._stopped = True
        self._queue.put(None)
        if wait:
            self._thread.quit()
            self._thread.wait(5000)

    def submit(self, command: Command) -> str:
        self._queue.put(command)
        return command.request_id

    def _run(self) -> None:
        while True:
            cmd = self._queue.get()
            if cmd is None:
                return
            handler = self._handlers.get(cmd.kind)
            if handler is None:
                self.resultReady.emit(Result(
                    request_id=cmd.request_id, kind=cmd.kind,
                    ok=False, error=f"handler not registered: {cmd.kind}",
                ))
                continue
            try:
                data = handler(dict(cmd.payload))
                self.resultReady.emit(Result(
                    request_id=cmd.request_id, kind=cmd.kind,
                    ok=True, data=data,
                ))
            except Exception:
                self.resultReady.emit(Result(
                    request_id=cmd.request_id, kind=cmd.kind,
                    ok=False, error=traceback.format_exc(),
                ))
