from __future__ import annotations

import importlib
from typing import Iterable

from amnesia.pipeline.hooks import HookRegistry


class PluginLoadError(RuntimeError):
    pass


def load_plugins(plugin_paths: Iterable[str], registry: HookRegistry) -> None:
    for plugin_path in plugin_paths:
        module_path, _, symbol = plugin_path.partition(":")
        if not module_path or not symbol:
            raise PluginLoadError(
                f"Invalid plugin '{plugin_path}'. Expected format module.path:function_name"
            )

        module = importlib.import_module(module_path)
        factory = getattr(module, symbol, None)
        if factory is None:
            raise PluginLoadError(f"Plugin function not found: {plugin_path}")

        factory(registry)
