---
name: make-pet-bead-patterns
description: Convert one or more pet photos (including HEIC, JPG, and PNG) into practical fuse-bead/perler patterns with blank backgrounds, numeric cell labels, MARD color codes, bead-count tables, and bead-style previews. Use whenever the user asks to make 拼豆图纸, fuse-bead patterns, Perler/Hama-style charts, color-by-number pet pixel art, multiple size variants, or numbered bead templates from pet photographs.
---

# Make Pet Bead Patterns

Create identity-faithful, buildable pet patterns rather than generic pixel-art animals.

## Required size gate

Do not infer a size when the user has not supplied one. Before processing images, ask exactly one concise question:

> 请告诉我需要的拼板尺寸，可多选，例如 15×15、20×20、25×25、30×30。

Accept ×, x, or *. Treat 15×15 as exact rows and columns. If the user provides centimeters instead, ask for bead diameter or confirm the converted grid. Default to 5 mm beads only when the user does not specify a diameter.

Read references/size-guide.md when recommending dimensions or color limits.

## Defaults

- Use MARD 5 mm colors from assets/mard.csv.
- Treat the exterior pure-white background as empty cells; do not place background beads.
- Keep white fur as actual white/cream beads.
- Produce a numeric chart by default. Also produce the MARD-code chart, bead-style preview, and CSV usage table.
- Use Chinese filenames and headings when the user communicates in Chinese.

## Workflow

1. Inspect every source image. For HEIC, convert a working copy with heif-convert; never overwrite the original.
2. Group photos by pet. Compare face shape, eyes, ears, nose, coat markings, expression, and accessories across references.
3. If the requested number of designs exceeds the available distinct photos, derive meaningfully different crops or poses from the clearest sources. Do not merely recolor one pattern.
4. Select references with sharp eyes and nose, complete ears, limited occlusion, and a characteristic expression.
5. Create a clean source image:
   - If the photo already has a clean background, use it directly.
   - Otherwise use the built-in image generation/editing workflow after viewing the local image.
   - Request a perfectly flat #FFFFFF background.
   - Preserve identity, pose, expression, coat markings, and proportions.
   - Remove people, furniture, leashes, and unrelated objects unless the user asks to retain an accessory.
   - Do not ask the model to create pixel art; pixelation must remain deterministic.
6. For multiple exact square sizes, reuse the same approved clean source and run the converter once per size.
7. Visually inspect every preview and at least one numbered chart per size. Confirm:
   - exact requested grid dimensions;
   - ears, eyes, nose, mouth, and tongue remain readable;
   - the outside background is empty;
   - white fur has not become holes;
   - cell numbers map correctly to the legend;
   - the legend is not clipped;
   - bead counts equal the number of filled cells.
8. Package outputs by size and provide a ZIP plus a contact-sheet overview when producing multiple variants.

## Run the converter

The bundled script requires Pillow and a clean white-background source:

    python scripts/make_bead_pattern.py \
      --source /absolute/path/pet-white-background.png \
      --output-dir /absolute/path/outputs \
      --name "金毛_正脸_20x20" \
      --size 20x20

Use --size 30×30 for an exact square or --size 56 to preserve the source aspect ratio at 56 columns. Override automatic color selection only when necessary:

    python scripts/make_bead_pattern.py ... --size 25x25 --colors 7

The script writes:

- name_MARD色号图纸.png
- name_数字编号图纸.png
- name_成品预览.png
- name_MARD用量表.csv

## White-background edit prompt

Use this structure and customize only the pet-specific invariants:

    Use case: precise-object-edit
    Primary request: Remove the entire environment and isolate this exact pet on a perfectly flat pure white #FFFFFF background.
    Subject invariants: preserve the exact face shape, eye size and spacing, ears, nose, muzzle, expression, tongue, coat markings, colors, pose, and proportions from the reference.
    Composition: center the pet with all important silhouette features visible and a modest white margin.
    Constraints: background must contain no shadow, gradient, floor, texture, people, furniture, leash, or text.
    Avoid: generic breed substitution, beautification, symmetry correction, larger eyes, cartoon styling, changed markings, watermark.

## Quality priorities

Prioritize identity over smooth gradients. At very small sizes, simplify fur before sacrificing eyes, nose, mouth, tongue, or signature markings. Prefer contiguous color regions and avoid isolated one-bead noise.

