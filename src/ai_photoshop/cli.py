import argparse
import json
import sys
from pathlib import Path

from ai_photoshop import __version__
from ai_photoshop.engine import apply_steps, describe, load_image, save_image
from ai_photoshop.ops import OPERATIONS, OperationError
from ai_photoshop.recipe import load_recipe, parse_recipe


def _steps_from_args(args) -> list:
    steps = []
    if args.recipe:
        steps += load_recipe(Path(args.recipe))
    for raw in args.op or []:
        try:
            item = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise OperationError(f"--op is not valid JSON: {exc}") from exc
        steps += parse_recipe([item])
    if not steps:
        raise OperationError("no steps given: use --recipe FILE and/or --op '{...}'")
    return steps


def _info(args) -> int:
    try:
        image = load_image(Path(args.image))
    except OperationError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(describe(image, Path(args.image)), indent=2))
    return 0


def _ops(args) -> int:
    catalogue = []
    for operation in OPERATIONS.values():
        params = []
        for param in operation.params:
            entry = {"name": param.name, "type": param.kind, "required": param.required}
            if param.default is not None:
                entry["default"] = param.default
            if param.minimum is not None:
                entry["minimum"] = param.minimum
            if param.maximum is not None:
                entry["maximum"] = param.maximum
            if param.choices:
                entry["choices"] = list(param.choices)
            params.append(entry)
        catalogue.append({"op": operation.name, "summary": operation.summary, "params": params})
    print(json.dumps(catalogue, indent=2, ensure_ascii=False))
    return 0


def _validate(args) -> int:
    try:
        steps = load_recipe(Path(args.recipe))
    except OperationError as exc:
        print(f"invalid: {exc}", file=sys.stderr)
        return 1
    print(f"valid: {len(steps)} step(s)")
    return 0


def _apply(args) -> int:
    source = Path(args.image)
    try:
        steps = _steps_from_args(args)
        image = load_image(source)
        result, log = apply_steps(image, steps)
        save_image(result, source, Path(args.output), force=args.force)
    except OperationError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(json.dumps({
        "input": describe(image, source),
        "output": {"file": Path(args.output).name, **describe(result)},
        "steps": log,
    }, indent=2))
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="ai-photoshop",
        description="Edit images with a recipe of explicit steps that an AI agent can write and check",
    )
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="command", required=True)

    info = sub.add_parser("info", help="Show an image's size, mode, and format as JSON")
    info.add_argument("image")
    info.set_defaults(func=_info)

    ops = sub.add_parser("ops", help="List every operation and its parameters as JSON")
    ops.set_defaults(func=_ops)

    validate = sub.add_parser("validate", help="Check a recipe file without touching any image")
    validate.add_argument("recipe")
    validate.set_defaults(func=_validate)

    apply = sub.add_parser("apply", help="Apply a recipe and write a new image")
    apply.add_argument("image", help="Input image; it is never changed")
    apply.add_argument("-o", "--output", required=True, help="Output file (.png, .jpg, .webp, .bmp, .tif)")
    apply.add_argument("--recipe", help="A JSON file with the steps")
    apply.add_argument("--op", action="append", help="One step as JSON, for example '{\"op\":\"flip\",\"axis\":\"horizontal\"}'. Repeat for more steps.")
    apply.add_argument("--force", action="store_true", help="Replace the output file if it exists")
    apply.set_defaults(func=_apply)

    args = parser.parse_args()
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
