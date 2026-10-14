# ai-photoshop

Edit images with explicit, checkable steps. An AI agent writes a recipe (a JSON list of operations), applies it to a copy of the image, looks at the result, and adjusts the recipe. The original image is never changed.

```bash
ai-photoshop info photo.png                       # size, mode, format
ai-photoshop ops                                  # every operation and its parameters, as JSON
ai-photoshop validate recipe.json                 # check a recipe without touching an image
ai-photoshop apply photo.png --recipe recipe.json -o edited.png
ai-photoshop apply photo.png --op '{"op":"grayscale"}' -o grey.png
```

A recipe is a list of steps, or an object with an `"ops"` list:

```json
{"ops": [
  {"op": "crop", "left": 0, "top": 0, "right": 800, "bottom": 450},
  {"op": "brightness", "factor": 1.2},
  {"op": "rectangle", "box": [40, 40, 360, 310], "color": "yellow", "width": 4},
  {"op": "text", "text": "Hello", "xy": [40, 380], "size": 36, "color": "black"}
]}
```

## Operations

| Operation | Parameters | What it does |
|---|---|---|
| `resize` | `width`, `height`, `keep_aspect` | Scale; a missing side is calculated when `keep_aspect` is true. |
| `crop` | `left`, `top`, `right`, `bottom` | Keep a rectangle, in pixels. |
| `rotate` | `degrees`, `expand`, `fill` | Rotate counter-clockwise; expands the canvas by default. |
| `flip` | `axis` (`horizontal` or `vertical`) | Mirror. |
| `brightness`, `contrast`, `saturation`, `sharpness` | `factor` | 1.0 is unchanged. |
| `blur` | `radius` | Gaussian blur. |
| `grayscale`, `invert` | none | Black and white; negative. |
| `rectangle` | `box`, `color`, `fill`, `width` | Outline or filled rectangle. |
| `text` | `text`, `xy`, `size`, `color`, `font` | Draw text at the top-left corner. |

`ai-photoshop ops` prints the full list, including types, ranges, and defaults, so an agent can read it before writing a recipe.

## Safety and checks

- **Validation before drawing.** Unknown operations, unknown parameters, wrong types, out-of-range values, and bad colours are refused with a message that names the step.
- **The input is never overwritten.** The output must be a different file, and an existing output needs `--force`.
- **Size limit.** Images above 50 million pixels are refused.
- **Report.** Each `apply` prints the input and output details and the size after every step, so a result can be checked without opening it.
- **Formats.** Output can be PNG, JPEG, WebP, BMP, or TIFF. JPEG drops transparency.

## Limits

- **Fonts:** `text` uses Pillow's default font unless you pass a `.ttf` or `.otf` file. Non-Latin text, such as Chinese, needs a font that contains those characters.
- **No selection or layers yet.** Operations apply to the whole image, or to a box you give.
- **Rectangles change the mode:** drawing converts the image to RGBA.
- **Not a photo-retouching tool.** It does exact, repeatable edits. Generative editing (inpainting, content-aware fill) is not included yet.

## Install

```bash
pip install -e .
```

Requires Python 3.10 or newer and Pillow.

## Licence

MIT. See [LICENSE](LICENSE).
