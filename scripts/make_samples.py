"""samples/ 폴더의 테스트용 샘플 이미지를 다시 만드는 개발용 스크립트.

샘플 이미지는 저장소에 이미 들어 있으므로 교사는 이 스크립트를 실행할 필요가 없습니다.
필요한 패키지: pillow, matplotlib (한국어 샘플에는 나눔고딕 등 한글 글꼴 경로를 --korean-font 로 지정)

    python scripts/make_samples.py --korean-font /path/to/NanumGothic.ttf
"""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

SAMPLES = Path(__file__).resolve().parent.parent / "samples"

ENGLISH_TEXT = """The Little Prince

"Goodbye," said the fox. "And now here is my secret, a very
simple secret: It is only with the heart that one can see rightly;
what is essential is invisible to the eye."

"What is essential is invisible to the eye," the little prince
repeated, so that he would be sure to remember."""

KOREAN_TEXT = """가정통신문

학부모님께
안녕하십니까? 다음 주 금요일에 과학 체험 학습이 있습니다.
학생들은 편한 복장과 필기도구를 준비해 주시기 바랍니다.
점심은 학교에서 제공하며, 오후 3시에 학교로 돌아옵니다.

2026년 9월 30일  ○○초등학교장"""

TABLE_ROWS = [
    ["Name", "Math", "English", "Science"],
    ["Minsu", "90", "85", "88"],
    ["Jiwoo", "78", "92", "81"],
    ["Seoyeon", "95", "89", "94"],
]


def _font(path: str | None, size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [path] if path else []
    candidates += ["DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]
    for candidate in candidates:
        if not candidate:
            continue
        try:
            return ImageFont.truetype(candidate, size)
        except OSError:
            continue
    import matplotlib  # noqa: PLC0415

    return ImageFont.truetype(str(Path(matplotlib.get_data_path()) / "fonts/ttf/DejaVuSans.ttf"), size)


def text_image(text: str, font: ImageFont.ImageFont, width: int = 1400) -> Image.Image:
    lines = text.split("\n")
    line_height = int(font.size * 1.6)  # type: ignore[attr-defined]
    image = Image.new("RGB", (width, line_height * len(lines) + 120), "white")
    draw = ImageDraw.Draw(image)
    for i, line in enumerate(lines):
        draw.text((60, 60 + i * line_height), line, fill=(20, 20, 20), font=font)
    return image


def table_image(font: ImageFont.ImageFont) -> Image.Image:
    col_w, row_h = 260, 80
    cols, rows = len(TABLE_ROWS[0]), len(TABLE_ROWS)
    image = Image.new("RGB", (col_w * cols + 80, row_h * rows + 80), "white")
    draw = ImageDraw.Draw(image)
    for r, row in enumerate(TABLE_ROWS):
        for c, value in enumerate(row):
            x, y = 40 + c * col_w, 40 + r * row_h
            if r == 0:
                draw.rectangle([x, y, x + col_w, y + row_h], fill=(230, 236, 245))
            draw.rectangle([x, y, x + col_w, y + row_h], outline=(40, 40, 40), width=2)
            draw.text((x + 24, y + 22), value, fill=(10, 10, 10), font=font)
    return image


def formula_image() -> Image.Image:
    import matplotlib  # noqa: PLC0415

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt  # noqa: PLC0415

    fig = plt.figure(figsize=(7, 1.6), dpi=200)
    fig.text(0.5, 0.5, r"$x = \frac{-b \pm \sqrt{b^{2} - 4ac}}{2a}$", fontsize=30, ha="center", va="center")
    path = SAMPLES / "_formula_tmp.png"
    fig.savefig(path, facecolor="white")
    plt.close(fig)
    image = Image.open(path).convert("RGB")
    path.unlink()
    return image


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--korean-font", default=None, help="한글 TTF 글꼴 경로")
    args = parser.parse_args()
    SAMPLES.mkdir(exist_ok=True)
    latin = _font(None, 38)
    text_image(ENGLISH_TEXT, latin).save(SAMPLES / "english_text.png", optimize=True)
    table_image(_font(None, 34)).save(SAMPLES / "table.png", optimize=True)
    formula_image().save(SAMPLES / "formula.png", optimize=True)
    if args.korean_font:
        text_image(KOREAN_TEXT, _font(args.korean_font, 38)).save(SAMPLES / "korean_text.png", optimize=True)
    print("샘플 이미지를 만들었어요:", sorted(p.name for p in SAMPLES.glob("*.png")))


if __name__ == "__main__":
    main()
