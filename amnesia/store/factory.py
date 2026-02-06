from __future__ import annotations

from amnesia.config import StoreConfig
from amnesia.store.base import Store
from amnesia.store.memory import InMemoryStore
from amnesia.store.sqlite import SQLiteStore


def build_store(config: StoreConfig) -> Store:
    backend = config.backend.lower()

    if backend == "sqlite":
        return SQLiteStore(config.dsn)
    if backend == "memory":
        return InMemoryStore()

    raise ValueError(f"Unsupported store backend: {config.backend}")
