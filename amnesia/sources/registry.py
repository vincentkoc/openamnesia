"""Source module registry and structure enforcement."""

from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module
import pkgutil


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


def validate_source_module_structure(source_name: str) -> None:
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
