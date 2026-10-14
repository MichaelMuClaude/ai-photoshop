"""Read and check an edit recipe: a list of operations, each a dict with an "op" key."""

import json
from pathlib import Path
from typing import Any

from PIL import ImageColor

from ai_photoshop.ops import OPERATIONS, OperationError, Param, _check_box, _check_point

FONT_SUFFIXES = (".ttf", ".otf")


def _coerce(param: Param, value: Any) -> Any:
    kind = param.kind
    if kind == "int":
        if isinstance(value, bool) or not isinstance(value, (int, float)) or int(value) != value:
            raise OperationError(f"{param.name} must be a whole number")
        value = int(value)
    elif kind == "float":
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise OperationError(f"{param.name} must be a number")
        value = float(value)
    elif kind == "bool":
        if not isinstance(value, bool):
            raise OperationError(f"{param.name} must be true or false")
    elif kind == "str":
        if not isinstance(value, str):
            raise OperationError(f"{param.name} must be text")
        if not value.strip():
            raise OperationError(f"{param.name} must not be empty")
        if param.maximum is not None and len(value) > param.maximum:
            raise OperationError(f"{param.name} must be at most {int(param.maximum)} characters")
        return value
    elif kind == "color":
        if not isinstance(value, str):
            raise OperationError(f"{param.name} must be a colour name or #rrggbb")
        try:
            ImageColor.getrgb(value)
        except ValueError as exc:
            raise OperationError(f"{param.name} is not a colour: {value!r}") from exc
    elif kind == "box":
        value = list(_check_box(value))
    elif kind == "point":
        value = list(_check_point(value))
    elif kind == "choice":
        if value not in param.choices:
            raise OperationError(f"{param.name} must be one of {', '.join(param.choices)}")
    elif kind == "path":
        if not isinstance(value, str) or not value.lower().endswith(FONT_SUFFIXES):
            raise OperationError(f"{param.name} must be a .ttf or .otf font file")
        if not Path(value).is_file():
            raise OperationError(f"{param.name} does not exist: {value}")
    if param.minimum is not None and isinstance(value, (int, float)) and value < param.minimum:
        raise OperationError(f"{param.name} must be at least {param.minimum}")
    if param.maximum is not None and isinstance(value, (int, float)) and value > param.maximum:
        raise OperationError(f"{param.name} must be at most {param.maximum}")
    return value


def parse_step(item: Any, position: int) -> tuple[str, dict]:
    where = f"step {position}"
    if not isinstance(item, dict) or "op" not in item:
        raise OperationError(f"{where}: each step must be an object with an \"op\" field")
    name = item["op"]
    if name not in OPERATIONS:
        raise OperationError(f"{where}: unknown operation {name!r} (see: ai-photoshop ops)")
    operation = OPERATIONS[name]
    known = {param.name for param in operation.params} | {"op"}
    extra = set(item) - known
    if extra:
        raise OperationError(f"{where} ({name}): unknown parameter(s) {', '.join(sorted(extra))}")

    params = {}
    for param in operation.params:
        if param.name in item:
            try:
                params[param.name] = _coerce(param, item[param.name])
            except OperationError as exc:
                raise OperationError(f"{where} ({name}): {exc}") from exc
        elif param.required:
            raise OperationError(f"{where} ({name}): missing {param.name}")
        elif param.default is not None:
            params[param.name] = param.default
    return name, params


def parse_recipe(data: Any) -> list[tuple[str, dict]]:
    """Accept a list of steps, or an object with an "ops" list."""
    if isinstance(data, dict):
        data = data.get("ops")
    if not isinstance(data, list) or not data:
        raise OperationError("a recipe must be a non-empty list of steps (or an object with an \"ops\" list)")
    return [parse_step(item, i) for i, item in enumerate(data, start=1)]


def load_recipe(path: Path) -> list[tuple[str, dict]]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise OperationError(f"{path.name} is not valid JSON: {exc}") from exc
    return parse_recipe(data)
