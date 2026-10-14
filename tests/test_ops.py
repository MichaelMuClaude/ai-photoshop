import json
import subprocess
import sys

import pytest
from PIL import Image

from ai_photoshop.engine import apply_steps, load_image, save_image
from ai_photoshop.ops import OPERATIONS, OperationError
from ai_photoshop.recipe import parse_recipe


def run_one(source, step):
    image = load_image(source)
    result, _ = apply_steps(image, parse_recipe([step]))
    return result


def test_catalogue_contains_the_documented_operations():
    assert {"resize", "crop", "rotate", "flip", "brightness", "contrast", "saturation",
            "sharpness", "blur", "grayscale", "invert", "rectangle", "text"} <= set(OPERATIONS)


def test_resize_keeps_aspect_ratio(sample_png):
    assert run_one(sample_png, {"op": "resize", "width": 50}).size == (50, 25)
    assert run_one(sample_png, {"op": "resize", "height": 20}).size == (40, 20)
    assert run_one(sample_png, {"op": "resize", "width": 60, "height": 60, "keep_aspect": False}).size == (60, 60)


def test_crop(sample_png):
    assert run_one(sample_png, {"op": "crop", "left": 10, "top": 5, "right": 60, "bottom": 45}).size == (50, 40)


def test_crop_outside_the_image_is_refused(sample_png):
    with pytest.raises(OperationError, match="outside the image"):
        run_one(sample_png, {"op": "crop", "left": 0, "top": 0, "right": 500, "bottom": 10})


def test_rotate_expands_the_canvas(sample_png):
    assert run_one(sample_png, {"op": "rotate", "degrees": 90}).size == (100, 200)


def test_flip_horizontal_moves_colours(sample_png):
    flipped = run_one(sample_png, {"op": "flip", "axis": "horizontal"})
    assert flipped.convert("RGB").getpixel((0, 0)) == (0, 0, 255)


def test_brightness_zero_is_black(sample_png):
    dark = run_one(sample_png, {"op": "brightness", "factor": 0}).convert("RGB")
    assert dark.getpixel((10, 10)) == (0, 0, 0)


def test_grayscale_makes_channels_equal(sample_png):
    grey = run_one(sample_png, {"op": "grayscale"}).convert("RGB")
    r, g, b = grey.getpixel((10, 10))
    assert r == g == b


def test_invert_red_becomes_cyan(sample_png):
    inverted = run_one(sample_png, {"op": "invert"}).convert("RGB")
    assert inverted.getpixel((10, 10)) == (0, 255, 255)


def test_rectangle_outline_uses_the_colour(sample_png):
    drawn = run_one(sample_png, {"op": "rectangle", "box": [5, 5, 50, 50], "color": "#00ff00", "width": 2})
    assert drawn.convert("RGB").getpixel((5, 20)) == (0, 255, 0)


def test_text_changes_pixels_and_keeps_size(sample_png):
    before = load_image(sample_png).convert("RGB")
    drawn = run_one(sample_png, {"op": "text", "text": "Hello", "xy": [10, 10], "size": 24, "color": "white"})
    assert drawn.size == before.size
    assert drawn.convert("RGB").tobytes() != before.tobytes()


@pytest.mark.parametrize(
    "step, message",
    [
        ({"op": "spin"}, "unknown operation"),
        ({"flip": 1}, "must be an object"),
        ({"op": "flip"}, "missing axis"),
        ({"op": "flip", "axis": "diagonal"}, "must be one of"),
        ({"op": "resize", "width": 2.5}, "whole number"),
        ({"op": "resize", "width": 0}, "at least 1"),
        ({"op": "brightness", "factor": "bright"}, "must be a number"),
        ({"op": "grayscale", "strength": 3}, "unknown parameter"),
        ({"op": "rectangle", "box": [5, 5, 1, 1]}, "right > left"),
        ({"op": "rectangle", "box": [1, 1, 9, 9], "color": "notacolour"}, "not a colour"),
        ({"op": "text", "text": "", "xy": [1, 1]}, "must not be empty"),
        ({"op": "text", "text": "x", "xy": [1, 1], "font": "/no/such/font.ttf"}, "does not exist"),
        ({"op": "text", "text": "x", "xy": [1, 1], "font": "notes.txt"}, "must be a .ttf or .otf"),
        ({"op": "blur", "radius": 99}, "at most"),
    ],
)
def test_invalid_steps_are_refused_with_a_reason(step, message):
    with pytest.raises(OperationError, match=message):
        parse_recipe([step])


def test_recipe_accepts_list_or_object():
    assert len(parse_recipe([{"op": "grayscale"}])) == 1
    assert len(parse_recipe({"ops": [{"op": "grayscale"}, {"op": "invert"}]})) == 2


def test_empty_recipe_is_refused():
    with pytest.raises(OperationError, match="non-empty"):
        parse_recipe([])


def test_steps_run_in_order(sample_png):
    image = load_image(sample_png)
    result, log = apply_steps(image, parse_recipe([
        {"op": "crop", "left": 0, "top": 0, "right": 100, "bottom": 50},
        {"op": "resize", "width": 20},
    ]))
    assert result.size == (20, 10)
    assert [entry["op"] for entry in log] == ["crop", "resize"]


def test_input_is_never_overwritten(sample_png, tmp_path):
    image = load_image(sample_png)
    with pytest.raises(OperationError, match="never overwritten"):
        save_image(image, sample_png, sample_png, force=True)


def test_existing_output_needs_force(sample_png, tmp_path):
    out = tmp_path / "out.png"
    out.write_bytes(b"x")
    with pytest.raises(OperationError, match="--force"):
        save_image(load_image(sample_png), sample_png, out)


def test_jpeg_output_drops_transparency(tmp_path):
    rgba = Image.new("RGBA", (10, 10), (255, 0, 0, 0))
    src = tmp_path / "t.png"
    rgba.save(src)
    out = tmp_path / "t.jpg"
    save_image(load_image(src), src, out)
    assert Image.open(out).mode == "RGB"


def test_unsupported_output_format_is_refused(sample_png, tmp_path):
    with pytest.raises(OperationError, match="cannot save as"):
        save_image(load_image(sample_png), sample_png, tmp_path / "out.gif")


def test_oversized_images_are_refused(sample_png, monkeypatch):
    import ai_photoshop.engine as engine

    monkeypatch.setattr(engine, "MAX_PIXELS", 100)
    with pytest.raises(OperationError, match="pixel limit"):
        load_image(sample_png)


def test_missing_image_is_refused(tmp_path):
    with pytest.raises(OperationError, match="no such image"):
        load_image(tmp_path / "nope.png")


def run_cli(*args):
    return subprocess.run([sys.executable, "-m", "ai_photoshop.cli", *args], capture_output=True, text=True)


def test_cli_apply_with_inline_ops(sample_png, tmp_path):
    out = tmp_path / "result.png"
    result = run_cli("apply", str(sample_png), "-o", str(out),
                     "--op", '{"op":"resize","width":50}', "--op", '{"op":"flip","axis":"vertical"}')
    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report["output"]["width"] == 50
    assert [s["op"] for s in report["steps"]] == ["resize", "flip"]
    assert Image.open(out).size == (50, 25)


def test_cli_apply_with_recipe_file(sample_png, tmp_path):
    recipe = tmp_path / "recipe.json"
    recipe.write_text(json.dumps({"ops": [{"op": "grayscale"}]}), encoding="utf-8")
    out = tmp_path / "grey.png"
    assert run_cli("apply", str(sample_png), "--recipe", str(recipe), "-o", str(out)).returncode == 0
    assert out.exists()


def test_cli_validate_and_info_and_ops(sample_png, tmp_path):
    good = tmp_path / "good.json"
    good.write_text('[{"op": "invert"}]', encoding="utf-8")
    bad = tmp_path / "bad.json"
    bad.write_text('[{"op": "explode"}]', encoding="utf-8")
    assert run_cli("validate", str(good)).returncode == 0
    assert run_cli("validate", str(bad)).returncode == 1
    info = json.loads(run_cli("info", str(sample_png)).stdout)
    assert (info["width"], info["height"]) == (200, 100)
    names = {entry["op"] for entry in json.loads(run_cli("ops").stdout)}
    assert "rectangle" in names
