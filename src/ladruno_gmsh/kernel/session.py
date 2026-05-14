"""Initialization and lifecycle of the gmsh context (process-wide singleton)."""
from __future__ import annotations

import threading
from contextlib import contextmanager
from typing import Iterator

import gmsh


class GmshSession:
    """Wrapper around gmsh's global state.

    gmsh exposes a single context per process and is neither reentrant
    nor thread-safe. This class centralizes ``initialize`` /
    ``finalize``, model creation and switching, and logger capture.

    Should not be instantiated directly. Use :func:`session`.
    """

    _instance: "GmshSession | None" = None
    _instance_lock = threading.Lock()

    def __init__(self) -> None:
        self._initialized = False
        self._lock = threading.RLock()

    @classmethod
    def instance(cls) -> "GmshSession":
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def initialize(self) -> None:
        with self._lock:
            if self._initialized:
                return
            gmsh.initialize()
            gmsh.option.setNumber("General.Terminal", 0)
            gmsh.option.setNumber("General.AbortOnError", 0)
            gmsh.logger.start()
            self._initialized = True

    def finalize(self) -> None:
        with self._lock:
            if not self._initialized:
                return
            try:
                gmsh.logger.stop()
            except Exception:
                pass
            try:
                gmsh.finalize()
            finally:
                self._initialized = False

    def ensure(self) -> None:
        if not self._initialized:
            self.initialize()

    @property
    def initialized(self) -> bool:
        return self._initialized

    def add_model(self, name: str) -> str:
        self.ensure()
        with self._lock:
            gmsh.model.add(name)
            return name

    def set_current(self, name: str) -> None:
        self.ensure()
        with self._lock:
            gmsh.model.setCurrent(name)

    def remove_model(self) -> None:
        self.ensure()
        with self._lock:
            gmsh.model.remove()

    def list_models(self) -> list[str]:
        self.ensure()
        with self._lock:
            return list(gmsh.model.list())

    def current_model(self) -> str:
        self.ensure()
        with self._lock:
            return gmsh.model.getCurrent()

    def drain_log(self) -> list[str]:
        self.ensure()
        with self._lock:
            return list(gmsh.logger.get())

    @contextmanager
    def use_model(self, name: str) -> Iterator[str]:
        self.set_current(name)
        yield name


def session() -> GmshSession:
    return GmshSession.instance()
