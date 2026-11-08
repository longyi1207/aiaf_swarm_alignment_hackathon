#!/usr/bin/env python3
"""Contact sheet of the built PDF pages (paper/build/contact.png) for layout review."""
import glob, subprocess
from pathlib import Path
from PIL import Image
B = Path(__file__).resolve().parents[1] / "build"
for f in B.glob("thumb-*.png"):
    f.unlink()
subprocess.run(["pdftoppm", "-png", "-r", "42", str(B / "paper.pdf"), str(B / "thumb")], check=True)
ims = [Image.open(f) for f in sorted(glob.glob(str(B / "thumb-*.png")))]
w, h = ims[0].size; cols = 6; rows = (len(ims) + cols - 1) // cols
sheet = Image.new("RGB", (cols * w + (cols - 1) * 6, rows * h + (rows - 1) * 6), (120, 120, 120))
for i, im in enumerate(ims):
    sheet.paste(im, ((i % cols) * (w + 6), (i // cols) * (h + 6)))
sheet.save(B / "contact.png"); print(len(ims), "pages")
