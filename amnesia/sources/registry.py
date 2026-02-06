"""Source module registry and structure enforcement."""

from __future__ import annotations

import pkgutil
from dataclasses import dataclass
from importlib import import_module
from pathlib import Path


@dataclass(slots=True)
class SourceModuleSpec:
    name: str
    module_path: str


REQUIRED_SUBMODULES = (
    "helpers",
    "reporting",
    "types",
)


SOURCE_MODULE_SPECS = {
    "imessage": SourceModuleSpec(name="imessage", module_path="amnesia.sources.imessage"),
    "cursor": SourceModuleSpec(name="cursor", module_path="amnesia.sources.cursor"),
    "codex": SourceModuleSpec(name="codex", module_path="amnesia.sources.codex"),
    "terminal": SourceModuleSpec(name="terminal", module_path="amnesia.sources.terminal"),
}


def register_source_module(source_name: str) -> None:
    module_path = f"amnesia.sources.{source_name}"
    SOURCE_MODULE_SPECS[source_name] = SourceModuleSpec(name=source_name, module_path=module_path)


def discover_local_source_modules() -> None:
    root = Path(__file__).resolve().parent
    for child in root.iterdir():
        if child.name.startswith("_") or child.name == "__pycache__":
            continue
        if not child.is_dir():
            continue
        if (child / "__init__.py").exists():
            register_source_module(child.name)


def validate_source_module_structure(source_name: str) -> None:
    discover_local_source_modules()
    spec = SOURCE_MODULE_SPECS.get(source_name)
    if spec is None:
        return

    for submodule in REQUIRED_SUBMODULES:
        import_module(f"{spec.module_path}.{submodule}")

    import_module(f"{spec.module_path}.{source_name}")
    ops_pkg = import_module(f"{spec.module_path}.ops")
    ops_names = [name for _, name, _ in pkgutil.iter_modules(ops_pkg.__path__)]
    if not any(name.endswith("_ops") for name in ops_names):
        raise RuntimeError(
            "Source "
            f"'{source_name}' missing required ops module "
            f"'*_ops.py' in {spec.module_path}.ops"
        )
