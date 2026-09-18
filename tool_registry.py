import importlib.util
from pathlib import Path


class ToolRegistry:
    def __init__(self):
        self._modules = {}

    def load_tools(self, tools_dir: Path):
        for path in sorted(tools_dir.glob("*.py")):
            if path.stem.startswith("_"):
                continue
            spec = importlib.util.spec_from_file_location(path.stem, path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            self._modules[mod.NAME] = mod

    def get_anthropic_tools(self) -> list[dict]:
        return [
            {
                "name": m.NAME,
                "description": m.DESCRIPTION,
                "input_schema": m.INPUT_SCHEMA,
            }
            for m in self._modules.values()
        ]

    def execute(self, name: str, params: dict, simulator) -> str:
        mod = self._modules.get(name)
        if not mod:
            return f"Error: tool '{name}' not registered."
        try:
            return mod.execute(params, simulator)
        except Exception as exc:
            return f"Tool error ({name}): {exc}"
