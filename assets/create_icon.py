"""Generate app_icon.ico for Windows desktop and exe embedding."""

from __future__ import annotations

from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    raise SystemExit("Install Pillow first: pip install pillow")

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "app_icon.ico"


def _draw_icon(size: int, purple: bool = False) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    pad = max(2, size // 16)
    outer = (106, 13, 173, 255) if purple else (139, 0, 0, 255)
    inner = (75, 0, 130, 255) if purple else (90, 0, 0, 255)
    glow = (200, 160, 255, 255) if purple else (255, 180, 180, 255)

    draw.ellipse([pad, pad, size - pad, size - pad], fill=outer)
    inset = pad + size // 8
    draw.ellipse([inset, inset, size - inset, size - inset], fill=inner)
    cx, cy = size // 2, size // 2
    r = size // 5
    draw.polygon(
        [(cx, cy - r), (cx + r, cy + r // 2), (cx - r, cy + r // 2)],
        fill=glow,
    )

    if size >= 48:
        label = "P" if purple else "R"
        try:
            font = ImageFont.truetype("arialbd.ttf", max(10, size // 3))
        except OSError:
            font = ImageFont.load_default()
        bbox = draw.textbbox((0, 0), label, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        draw.text((cx - tw // 2, cy + r // 4 - th // 2), label, fill=(255, 255, 255, 240), font=font)

    return img


def main() -> None:
    red = _draw_icon(256, purple=False)
    sizes = [(16, red.resize((16, 16), Image.Resampling.LANCZOS)), (32, red.resize((32, 32), Image.Resampling.LANCZOS)),
             (48, red.resize((48, 48), Image.Resampling.LANCZOS)), (256, red)]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    sizes[1][1].save(OUT, format="ICO", sizes=[(s, s) for s, _ in sizes])
    print(f"Created {OUT}")


if __name__ == "__main__":
    main()
