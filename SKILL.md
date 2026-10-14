---
name: ai-photoshop
description: Edit an image with a recipe of explicit steps (crop, resize, rotate, brightness, rectangles, text, and more). Use when the user asks to change, crop, annotate, or adjust an image. The original file is never overwritten, and each result can be viewed and corrected.
---

# ai-photoshop

## Workflow

1. Check the image: `ai-photoshop info photo.png`.
2. Read the operations: `ai-photoshop ops`. Use only the parameters it lists.
3. Write a recipe as JSON, for example `{"ops": [{"op": "crop", "left": 0, "top": 0, "right": 800, "bottom": 450}]}`.
4. Check it: `ai-photoshop validate recipe.json`. Fix any reported step.
5. Apply it to a new file: `ai-photoshop apply photo.png --recipe recipe.json -o edited.png`.
6. Look at `edited.png` with the Read tool, and compare it with what the user asked for.
7. If something is wrong, edit the recipe and apply again to a new file name. Do not overwrite earlier results.

For a single step, use `--op`: `ai-photoshop apply photo.png --op '{"op":"grayscale"}' -o grey.png`.

## Rules

- Never write to the input file. Always use a new output name.
- Pixel coordinates start at the top-left corner, and `box` is `[left, top, right, bottom]`.
- Colours are names such as `red` or `#ff8800`.
- Text needs a font file for non-Latin characters. Ask the user for one if the text is not Latin.
- The steps run in order, so a crop before a resize is not the same as a resize before a crop.

## Limits

- Operations apply to the whole image, or to a box you give. There are no layers or selections yet.
- No generative editing such as removing objects or filling areas.
