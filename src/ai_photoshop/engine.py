"""Load an image, apply recipe steps in order, and save the result."""

from pathlib import Path

from PIL import Image

from ai_photoshop.ops import MAX_PIXELS, OPERATIONS, OperationError

SAVE_FORMATS = {
    ".png": "PNG",
    ".jpg": "JPEG",
    ".jpeg": "JPEG",
    ".webp": "WEBP",
    ".bmp": "BMP",
    ".tif": "TIFF",
    ".tiff": "TIFF",
}


def load_image(path: Path) -> Image.Image:
    if not path.is_file():
        raise OperationError(f"no such image: {path}")
    try:
        image = Image.open(path)
        width, height = image.size
    except Exception as exc:  # Pillow raises several types for unreadable files
        raise OperationError(f"cannot read {path.name} as an image: {exc}") from exc
    if width * height > MAX_PIXELS:
        raise OperationError(f"image is {width}x{height}, above the {MAX_PIXELS:,}-pixel limit")
    image.load()
    return image


def describe(image: Image.Image, path: Path | None = None) -> dict:
    info = {
        "width": image.width,
        "height": image.height,
        "mode": image.mode,
        "has_alpha": "A" in image.getbands(),
        "format": image.format,
    }
    if path is not None:
        info = {"file": path.name, **info}
    return info


def apply_steps(image: Image.Image, steps: list[tuple[str, dict]]) -> tuple[Image.Image, list[dict]]:
    log = []
    for number, (name, params) in enumerate(steps, start=1):
        image = OPERATIONS[name].apply(image, params)
        log.append({"step": number, "op": name, "width": image.width, "height": image.height, "mode": image.mode})
    return image, log


def save_image(image: Image.Image, source: Path, output: Path, force: bool = False) -> None:
    if output.resolve() == source.resolve():
        raise OperationError("the output must be a different file from the input; the original is never overwritten")
    if output.exists() and not force:
        raise OperationError(f"{output} already exists (use --force to replace it)")
    fmt = SAVE_FORMATS.get(output.suffix.lower())
    if fmt is None:
        raise OperationError(f"cannot save as {output.suffix or 'no extension'}; use one of {', '.join(SAVE_FORMATS)}")
    if fmt == "JPEG" and image.mode not in ("RGB", "L"):
        image = image.convert("RGB")  # JPEG has no transparency
    if fmt == "BMP" and image.mode not in ("RGB", "L"):
        image = image.convert("RGB")
    output.parent.mkdir(parents=True, exist_ok=True)
    image.save(output, format=fmt)
