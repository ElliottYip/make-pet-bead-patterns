from __future__ import annotations

import csv
import math
import argparse
from collections import Counter, deque
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]


def parse_size(value: str) -> tuple[int, int | None]:
    normalized = value.lower().replace("×", "x").replace("*", "x")
    if "x" in normalized:
        width, height = normalized.split("x", 1)
        w, h = int(width), int(height)
        if w < 5 or h < 5 or w > 200 or h > 200:
            raise argparse.ArgumentTypeError("尺寸必须在 5×5 到 200×200 之间")
        return w, h
    width = int(normalized)
    if width < 5 or width > 200:
        raise argparse.ArgumentTypeError("宽度必须在 5 到 200 之间")
    return width, None


parser = argparse.ArgumentParser(description="将纯白背景的宠物图像转换为带数字编号和 MARD 色号的拼豆图纸。")
parser.add_argument("--source", type=Path, required=True, help="纯白背景的 PNG/JPG 宠物图像")
parser.add_argument("--output-dir", type=Path, required=True, help="输出目录")
parser.add_argument("--name", required=True, help="图纸名称")
parser.add_argument("--size", type=parse_size, required=True, help="尺寸，如 15x15、30×30 或 56")
parser.add_argument("--colors", type=int, help="最大颜色数；省略时按尺寸自动选择")
parser.add_argument("--palette", type=Path, default=ROOT / "assets" / "mard.csv", help="MARD 色卡 CSV")
args = parser.parse_args()

SOURCE = args.source
PALETTE_CSV = args.palette
OUTPUT_DIR = args.output_dir
DESIGN_NAME = args.name
GRID_W, GRID_H_OVERRIDE = args.size
if args.colors:
    MAX_COLORS = args.colors
else:
    longest = max(GRID_W, GRID_H_OVERRIDE or GRID_W)
    MAX_COLORS = 5 if longest <= 15 else 6 if longest <= 20 else 7 if longest <= 25 else 8 if longest <= 30 else 10 if longest <= 40 else 12
OUT_PATTERN = OUTPUT_DIR / f"{DESIGN_NAME}_MARD色号图纸.png"
OUT_NUMBERED = OUTPUT_DIR / f"{DESIGN_NAME}_数字编号图纸.png"
OUT_PREVIEW = OUTPUT_DIR / f"{DESIGN_NAME}_成品预览.png"
OUT_USAGE = OUTPUT_DIR / f"{DESIGN_NAME}_MARD用量表.csv"
CELL = 32


def rgb_to_lab(rgb: tuple[int, int, int]) -> tuple[float, float, float]:
    vals = []
    for v in rgb:
        x = v / 255.0
        vals.append(x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4)
    r, g, b = vals
    x = (r * 0.4124 + g * 0.3576 + b * 0.1805) / 0.95047
    y = r * 0.2126 + g * 0.7152 + b * 0.0722
    z = (r * 0.0193 + g * 0.1192 + b * 0.9505) / 1.08883

    def f(t: float) -> float:
        return t ** (1 / 3) if t > 0.008856 else 7.787 * t + 16 / 116

    fx, fy, fz = f(x), f(y), f(z)
    return (116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz))


def distance(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


def load_mard() -> list[dict]:
    rows = []
    with PALETTE_CSV.open(newline="", encoding="utf-8") as fh:
        for code, name, r, g, b, _contributor in csv.reader(fh):
            rgb = (int(r), int(g), int(b))
            rows.append({"code": code, "name": name, "rgb": rgb, "lab": rgb_to_lab(rgb)})
    return rows


def best_text_color(rgb: tuple[int, int, int]) -> tuple[int, int, int]:
    luminance = 0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2]
    return (255, 255, 255) if luminance < 130 else (20, 20, 20)


def font(size: int, bold: bool = False):
    candidates = [
        "/System/Library/Fonts/STHeiti Medium.ttc" if bold else
        "/System/Library/Fonts/STHeiti Light.ttc",
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size=size)
        except OSError:
            pass
    return ImageFont.load_default()


def main() -> None:
    OUT_PATTERN.parent.mkdir(parents=True, exist_ok=True)
    src = Image.open(SOURCE).convert("RGB")
    if GRID_H_OVERRIDE is not None:
        grid_h = GRID_H_OVERRIDE
        target_ratio = GRID_W / grid_h
        source_ratio = src.width / src.height
        if source_ratio < target_ratio:
            # Portrait source: keep ears and face, crop excess chest from the bottom.
            crop_h = round(src.width / target_ratio)
            src = src.crop((0, 0, src.width, crop_h))
        elif source_ratio > target_ratio:
            crop_w = round(src.height * target_ratio)
            left = (src.width - crop_w) // 2
            src = src.crop((left, 0, left + crop_w, src.height))
    else:
        ratio = src.height / src.width
        grid_h = round(GRID_W * ratio)
    small = src.resize((GRID_W, grid_h), Image.Resampling.BOX)

    # Remove only white pixels connected to the canvas edge. This preserves white fur,
    # eye highlights and clothing details inside the subject.
    pixels = list(small.getdata())
    background = [False] * (GRID_W * grid_h)
    queue = deque()
    for x in range(GRID_W):
        queue.append((x, 0))
        queue.append((x, grid_h - 1))
    for y in range(grid_h):
        queue.append((0, y))
        queue.append((GRID_W - 1, y))

    def is_backdrop(px: tuple[int, int, int]) -> bool:
        return min(px) >= 248 and max(px) - min(px) <= 8

    while queue:
        x, y = queue.popleft()
        i = y * GRID_W + x
        if background[i] or not is_backdrop(pixels[i]):
            continue
        background[i] = True
        if x:
            queue.append((x - 1, y))
        if x + 1 < GRID_W:
            queue.append((x + 1, y))
        if y:
            queue.append((x, y - 1))
        if y + 1 < grid_h:
            queue.append((x, y + 1))
    active = [not is_bg for is_bg in background]

    # Quantize only the dog colors. A neutral filler avoids wasting a palette slot on white.
    dog_pixels = [px for px, on in zip(small.getdata(), active) if on]
    strip = Image.new("RGB", (len(dog_pixels), 1))
    strip.putdata(dog_pixels)
    quant = strip.quantize(colors=MAX_COLORS, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    q_palette = quant.getpalette()
    q_indices = list(quant.getdata())

    mard = load_mard()
    q_to_mard = {}
    for q in sorted(set(q_indices)):
        rgb = tuple(q_palette[q * 3:q * 3 + 3])
        lab = rgb_to_lab(rgb)
        q_to_mard[q] = min(mard, key=lambda row: distance(lab, row["lab"]))

    pattern = [None] * (GRID_W * grid_h)
    q_iter = iter(q_indices)
    for i, on in enumerate(active):
        if on:
            pattern[i] = q_to_mard[next(q_iter)]

    # Remove stray one-pixel islands by borrowing the dominant neighboring color.
    for _ in range(2):
        updated = pattern[:]
        for y in range(grid_h):
            for x in range(GRID_W):
                i = y * GRID_W + x
                if pattern[i] is None:
                    continue
                neighbors = []
                for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < GRID_W and 0 <= ny < grid_h:
                        p = pattern[ny * GRID_W + nx]
                        if p is not None:
                            neighbors.append(p["code"])
                if len(neighbors) >= 3 and pattern[i]["code"] not in neighbors:
                    winner = Counter(neighbors).most_common(1)[0][0]
                    updated[i] = next(row for row in mard if row["code"] == winner)
        pattern = updated

    counts = Counter(p["code"] for p in pattern if p is not None)
    used = {p["code"]: p for p in pattern if p is not None}
    order = [used[code] for code, _ in counts.most_common()]
    number_for = {row["code"]: str(i + 1) for i, row in enumerate(order)}

    with OUT_USAGE.open("w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.writer(fh)
        writer.writerow(["MARD色号", "颜色名", "RGB", "数量"])
        for row in order:
            writer.writerow([row["code"], row["name"], "/".join(map(str, row["rgb"])), counts[row["code"]]])
        writer.writerow(["合计", "", "", sum(counts.values())])

    margin_l, margin_t = 58, 94
    legend_cols = 2 if GRID_W < 30 else 4
    legend_h = 96 + math.ceil(len(order) / legend_cols) * 58
    canvas_w = max(margin_l + GRID_W * CELL + 34, 1000)
    canvas = Image.new("RGB", (canvas_w, margin_t + grid_h * CELL + legend_h), "white")
    d = ImageDraw.Draw(canvas)
    title_f = font(30, True)
    body_f = font(18)
    code_f = font(13, True)
    small_f = font(14)
    size_label = f"{GRID_W}×{grid_h}" if GRID_H_OVERRIDE is not None else f"{GRID_W}格"
    d.text((margin_l, 18), f"{DESIGN_NAME} · MARD 5mm · {size_label}", fill="#151515", font=title_f)
    d.text((margin_l, 56), f"有效豆数 {sum(counts.values())} · 使用 {len(order)} 色 · 空白格不放豆", fill="#555555", font=body_f)

    for y in range(grid_h):
        for x in range(GRID_W):
            x0, y0 = margin_l + x * CELL, margin_t + y * CELL
            row = pattern[y * GRID_W + x]
            fill = row["rgb"] if row else (255, 255, 255)
            d.rectangle((x0, y0, x0 + CELL, y0 + CELL), fill=fill, outline="#b8b8b8", width=1)
            if row:
                code = row["code"]
                box = d.textbbox((0, 0), code, font=code_f)
                tw, th = box[2] - box[0], box[3] - box[1]
                d.text((x0 + (CELL - tw) / 2, y0 + (CELL - th) / 2 - 1), code,
                       fill=best_text_color(row["rgb"]), font=code_f)

    for x in range(GRID_W):
        if (x + 1) % 5 == 0:
            tx = margin_l + x * CELL + CELL / 2
            label = str(x + 1)
            box = d.textbbox((0, 0), label, font=small_f)
            d.text((tx - (box[2] - box[0]) / 2, margin_t - 23), label, fill="#555", font=small_f)
    for y in range(grid_h):
        if (y + 1) % 5 == 0:
            label = str(y + 1)
            box = d.textbbox((0, 0), label, font=small_f)
            d.text((margin_l - 10 - (box[2] - box[0]), margin_t + y * CELL + 8), label, fill="#555", font=small_f)

    # Heavy guide lines every five beads.
    for x in range(0, GRID_W + 1, 5):
        xx = margin_l + x * CELL
        d.line((xx, margin_t, xx, margin_t + grid_h * CELL), fill="#666", width=2)
    for y in range(0, grid_h + 1, 5):
        yy = margin_t + y * CELL
        d.line((margin_l, yy, margin_l + GRID_W * CELL, yy), fill="#666", width=2)

    ly = margin_t + grid_h * CELL + 32
    d.text((margin_l, ly), "色号与用量", fill="#151515", font=font(24, True))
    ly += 42
    col_w = (canvas.width - margin_l - 34) // legend_cols
    for idx, row in enumerate(order):
        col, rr = idx % legend_cols, idx // legend_cols
        x, y = margin_l + col * col_w, ly + rr * 58
        d.rounded_rectangle((x, y, x + 42, y + 42), radius=6, fill=row["rgb"], outline="#888")
        d.text((x + 52, y + 1), f'{row["code"]}  × {counts[row["code"]]}', fill="#111", font=body_f)
        d.text((x + 52, y + 23), f'RGB {row["rgb"][0]},{row["rgb"][1]},{row["rgb"][2]}', fill="#666", font=small_f)

    canvas.save(OUT_PATTERN, quality=95)

    # Common color-by-number edition: cells use 1..N; legend maps numbers to brand codes.
    numbered = canvas.copy()
    nd = ImageDraw.Draw(numbered)
    nd.rectangle((0, 0, numbered.width, numbered.height), fill="white")
    nd.text((margin_l, 18), f"{DESIGN_NAME} · 数字编号版 · {size_label}", fill="#151515", font=title_f)
    nd.text((margin_l, 56), f"有效豆数 {sum(counts.values())} · 使用 {len(order)} 色 · 格内数字对应下方图例", fill="#555555", font=body_f)
    number_f = font(16, True)
    for y in range(grid_h):
        for x in range(GRID_W):
            x0, y0 = margin_l + x * CELL, margin_t + y * CELL
            row = pattern[y * GRID_W + x]
            fill = row["rgb"] if row else (255, 255, 255)
            nd.rectangle((x0, y0, x0 + CELL, y0 + CELL), fill=fill, outline="#b8b8b8", width=1)
            if row:
                label = number_for[row["code"]]
                box = nd.textbbox((0, 0), label, font=number_f)
                tw, th = box[2] - box[0], box[3] - box[1]
                nd.text((x0 + (CELL - tw) / 2, y0 + (CELL - th) / 2 - 1), label,
                        fill=best_text_color(row["rgb"]), font=number_f)
    for x in range(GRID_W):
        if (x + 1) % 5 == 0:
            tx = margin_l + x * CELL + CELL / 2
            label = str(x + 1)
            box = nd.textbbox((0, 0), label, font=small_f)
            nd.text((tx - (box[2] - box[0]) / 2, margin_t - 23), label, fill="#555", font=small_f)
    for y in range(grid_h):
        if (y + 1) % 5 == 0:
            label = str(y + 1)
            box = nd.textbbox((0, 0), label, font=small_f)
            nd.text((margin_l - 10 - (box[2] - box[0]), margin_t + y * CELL + 8), label, fill="#555", font=small_f)
    for x in range(0, GRID_W + 1, 5):
        xx = margin_l + x * CELL
        nd.line((xx, margin_t, xx, margin_t + grid_h * CELL), fill="#666", width=2)
    for y in range(0, grid_h + 1, 5):
        yy = margin_t + y * CELL
        nd.line((margin_l, yy, margin_l + GRID_W * CELL, yy), fill="#666", width=2)
    nd.text((margin_l, ly - 42), "数字、色号与用量", fill="#151515", font=font(24, True))
    for idx, row in enumerate(order):
        col, rr = idx % legend_cols, idx // legend_cols
        x, y = margin_l + col * col_w, ly + rr * 58
        nd.rounded_rectangle((x, y, x + 42, y + 42), radius=6, fill=row["rgb"], outline="#888")
        num = number_for[row["code"]]
        nd.text((x + 52, y + 1), f'{num} → {row["code"]}  × {counts[row["code"]]}', fill="#111", font=body_f)
        nd.text((x + 52, y + 23), f'RGB {row["rgb"][0]},{row["rgb"][1]},{row["rgb"][2]}', fill="#666", font=small_f)
    numbered.save(OUT_NUMBERED, quality=95)

    preview_cell = 22
    preview = Image.new("RGB", (GRID_W * preview_cell, grid_h * preview_cell), "white")
    pd = ImageDraw.Draw(preview)
    for y in range(grid_h):
        for x in range(GRID_W):
            row = pattern[y * GRID_W + x]
            if row:
                x0, y0 = x * preview_cell, y * preview_cell
                pd.rectangle((x0, y0, x0 + preview_cell, y0 + preview_cell), fill=row["rgb"])
                pd.ellipse((x0 + 3, y0 + 3, x0 + preview_cell - 3, y0 + preview_cell - 3),
                           fill=row["rgb"], outline=(255, 255, 255), width=1)
                pd.ellipse((x0 + 8, y0 + 8, x0 + preview_cell - 8, y0 + preview_cell - 8),
                           fill=(245, 245, 245))
    preview.save(OUT_PREVIEW)

    print(OUT_PATTERN)
    print(OUT_NUMBERED)
    print(OUT_PREVIEW)
    print(OUT_USAGE)
    print(f"{GRID_W}x{grid_h}, {sum(counts.values())} beads, {len(order)} colors")


if __name__ == "__main__":
    main()
