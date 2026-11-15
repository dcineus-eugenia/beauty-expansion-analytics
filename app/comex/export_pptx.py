"""Export the HTML deck to PowerPoint: one full-slide image per slide, no speaker notes.

    python app/comex/build_dashboard.py      # first: rebuild slides_comex.html
    python app/comex/export_pptx.py          # then: writes app/comex/Sephora_Europe_2027_Comex.pptx

Needs Google Chrome (headless print to PDF), poppler's `pdftoppm` and `python-pptx` (pip install python-pptx).
Set CHROME=/path/to/chrome if Chrome is not in the default macOS location.
"""
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
DECK = HERE / "slides_comex.html"
OUT = HERE / "Sephora_Europe_2027_Comex.pptx"
CHROME = os.environ.get("CHROME", "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")


def main() -> None:
    try:
        from pptx import Presentation
        from pptx.util import Emu
    except ImportError:
        sys.exit("python-pptx is missing: pip install python-pptx")
    if not pathlib.Path(CHROME).exists():
        sys.exit(f"Chrome not found at {CHROME}: set CHROME=/path/to/chrome")
    if shutil.which("pdftoppm") is None:
        sys.exit("pdftoppm is missing: install poppler (brew install poppler)")

    with tempfile.TemporaryDirectory() as tmp:
        pdf = pathlib.Path(tmp) / "deck.pdf"
        subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--no-pdf-header-footer", "--virtual-time-budget=3000",
                        f"--print-to-pdf={pdf}", DECK.as_uri()], check=True, capture_output=True)
        subprocess.run(["pdftoppm", "-r", "220", "-png", str(pdf), str(pathlib.Path(tmp) / "s")], check=True)
        images = sorted(pathlib.Path(tmp).glob("s-*.png"))
        if not images:
            sys.exit("Chrome produced no pages")
        prs = Presentation()
        prs.slide_width, prs.slide_height = Emu(12192000), Emu(6858000)          # 16:9
        for img in images:
            slide = prs.slides.add_slide(prs.slide_layouts[6])
            slide.shapes.add_picture(str(img), 0, 0, prs.slide_width, prs.slide_height)
        prs.save(OUT)
    print(f"wrote {OUT.relative_to(HERE.parents[1])} ({len(images)} slides, no notes)")


if __name__ == "__main__":
    main()
