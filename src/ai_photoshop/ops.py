"""The editing operations an agent can ask for, with their parameters and their Pillow code.

Every operation is described by OPERATIONS, so the same list drives validation,
the `ops` command that agents read, and the documentation.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from PIL import Image, ImageColor, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps

MAX_PIXELS = 50_000_000  # refuse larger inputs; decoding them is slow and memory-hungry
MAX_DIMENSION = 10_000


class OperationError(ValueError):
    """A recipe or parameter is not valid. The message is meant for the user or agent."""


@dataclass(frozen=True)
class Param:
    name: str
    kind: str  # "int", "float", "str", "bool", "color", "box", "point", "choice", "path"
    required: bool = True
    default: Any = None
    minimum: float | None = None
    maximum: float | None = None
    choices: tuple[str, ...] = ()
    help: str = ""


@dataclass(frozen=True)
class Operation:
    name: str
    summary: str
    params: tuple[Param, ...]
    apply: Callable[[Image.Image, dict], Image.Image]
    fields: dict = field(default_factory=dict)


def _check_box(value, image_size=None):
    if not (isinstance(value, (list, tuple)) and len(value) == 4):
        raise OperationError("box must be [left, top, right, bottom]")
    left, top, right, bottom = (int(v) for v in value)
    if right <= left or bottom <= top:
        raise OperationError("box must have right > left and bottom > top")
    return left, top, right, bottom


def _resize(image, p):
    width, height = image.size
    new_w = p.get("width")
    new_h = p.get("height")
    if new_w is None and new_h is None:
        raise OperationError("resize needs width, height, or both")
    if p.get("keep_aspect", True):
        if new_w is None:
            new_w = round(width * new_h / height)
        elif new_h is None:
            new_h = round(height * new_w / width)
    else:
        new_w = new_w or width
        new_h = new_h or height
    return image.resize((int(new_w), int(new_h)), Image.Resampling.LANCZOS)


def _crop(image, p):
    box = _check_box([p["left"], p["top"], p["right"], p["bottom"]])
    if box[2] > image.width or box[3] > image.height:
        raise OperationError(f"crop box {box} is outside the image of size {image.size}")
    return image.crop(box)


def _rotate(image, p):
    fill = ImageColor.getrgb(p.get("fill", "white"))
    return image.rotate(p["degrees"], resample=Image.Resampling.BICUBIC, expand=p.get("expand", True), fillcolor=fill)


def _flip(image, p):
    if p["axis"] == "horizontal":
        return ImageOps.mirror(image)
    return ImageOps.flip(image)


def _enhance(enhancer):
    def run(image, p):
        return enhancer(image).enhance(p["factor"])
    return run


def _blur(image, p):
    return image.filter(ImageFilter.GaussianBlur(p["radius"]))


def _grayscale(image, p):
    return ImageOps.grayscale(image.convert("RGB")).convert("RGB")


def _invert(image, p):
    if image.mode == "RGBA":
        r, g, b, a = image.split()
        return Image.merge("RGBA", (*ImageOps.invert(Image.merge("RGB", (r, g, b))).split(), a))
    return ImageOps.invert(image.convert("RGB"))


def _rectangle(image, p):
    box = _check_box(p["box"])
    color = ImageColor.getrgb(p["color"])
    out = image.convert("RGBA")
    draw = ImageDraw.Draw(out)
    if p.get("fill", False):
        draw.rectangle(box, fill=color)
    else:
        draw.rectangle(box, outline=color, width=p.get("width", 3))
    return out


def _text(image, p):
    text = p["text"]
    color = ImageColor.getrgb(p.get("color", "black"))
    font_path = p.get("font")
    if font_path:
        font = ImageFont.truetype(font_path, p.get("size", 32))
    else:
        font = ImageFont.load_default(size=p.get("size", 32))
    out = image.convert("RGBA")
    draw = ImageDraw.Draw(out)
    draw.text(tuple(p["xy"]), text, fill=color, font=font)
    return out


def _check_point(value):
    if not (isinstance(value, (list, tuple)) and len(value) == 2):
        raise OperationError("xy must be [x, y]")
    return int(value[0]), int(value[1])


def _text_wrapper(image, p):
    p = dict(p)
    p["xy"] = _check_point(p["xy"])
    return _text(image, p)


OPERATIONS: dict[str, Operation] = {}


def _register(name, summary, params, apply):
    OPERATIONS[name] = Operation(name, summary, tuple(params), apply)


_register(
    "resize",
    "Scale the image to a width and/or height. With keep_aspect (default), a missing side is calculated.",
    [
        Param("width", "int", required=False, minimum=1, maximum=MAX_DIMENSION),
        Param("height", "int", required=False, minimum=1, maximum=MAX_DIMENSION),
        Param("keep_aspect", "bool", required=False, default=True),
    ],
    _resize,
)
_register(
    "crop",
    "Keep only the rectangle between left, top, right, and bottom (pixels).",
    [
        Param("left", "int", minimum=0),
        Param("top", "int", minimum=0),
        Param("right", "int", minimum=1),
        Param("bottom", "int", minimum=1),
    ],
    _crop,
)
_register(
    "rotate",
    "Rotate counter-clockwise by degrees. Expands the canvas unless expand is false.",
    [
        Param("degrees", "float", minimum=-360, maximum=360),
        Param("expand", "bool", required=False, default=True),
        Param("fill", "color", required=False, default="white"),
    ],
    _rotate,
)
_register(
    "flip",
    "Mirror the image left-right (horizontal) or top-bottom (vertical).",
    [Param("axis", "choice", choices=("horizontal", "vertical"))],
    _flip,
)
_register(
    "brightness",
    "Multiply brightness. 1.0 leaves it unchanged; 0 is black; 2 is twice as bright.",
    [Param("factor", "float", minimum=0, maximum=5)],
    _enhance(lambda img: ImageEnhance.Brightness(img)),
)
_register(
    "contrast",
    "Multiply contrast. 1.0 leaves it unchanged; 0 is grey.",
    [Param("factor", "float", minimum=0, maximum=5)],
    _enhance(lambda img: ImageEnhance.Contrast(img)),
)
_register(
    "saturation",
    "Multiply colour saturation. 1.0 leaves it unchanged; 0 is greyscale.",
    [Param("factor", "float", minimum=0, maximum=5)],
    _enhance(lambda img: ImageEnhance.Color(img)),
)
_register(
    "sharpness",
    "Multiply sharpness. 1.0 leaves it unchanged; 0 is blurred; 2 is sharper.",
    [Param("factor", "float", minimum=0, maximum=5)],
    _enhance(lambda img: ImageEnhance.Sharpness(img)),
)
_register(
    "blur",
    "Gaussian blur with the given radius in pixels.",
    [Param("radius", "float", minimum=0, maximum=50)],
    _blur,
)
_register("grayscale", "Convert to black and white.", [], _grayscale)
_register("invert", "Invert the colours (negative).", [], _invert)
_register(
    "rectangle",
    "Draw a rectangle between box = [left, top, right, bottom]; outline or filled.",
    [
        Param("box", "box"),
        Param("color", "color", required=False, default="red"),
        Param("fill", "bool", required=False, default=False),
        Param("width", "int", required=False, default=3, minimum=1, maximum=200),
    ],
    _rectangle,
)
_register(
    "text",
    "Draw text at xy = [x, y] (top-left corner). Pass a font path (.ttf or .otf) for non-Latin text.",
    [
        Param("text", "str", maximum=200),
        Param("xy", "point"),
        Param("size", "int", required=False, default=32, minimum=6, maximum=500),
        Param("color", "color", required=False, default="black"),
        Param("font", "path", required=False),
    ],
    _text_wrapper,
)
