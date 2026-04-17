"""Load static context files (data directory next to this module)."""

from pathlib import Path
import json
from pypdf import PdfReader

_DATA = Path(__file__).resolve().parent / "data"

# Read LinkedIn / resume PDF
try:
    _reader = PdfReader(str(_DATA / "linkedin.pdf"))
    linkedin = ""
    for page in _reader.pages:
        text = page.extract_text()
        if text:
            linkedin += text
except FileNotFoundError:
    linkedin = "LinkedIn profile not available"

with open(_DATA / "summary.txt", "r", encoding="utf-8") as f:
    summary = f.read()

with open(_DATA / "style.txt", "r", encoding="utf-8") as f:
    style = f.read()

with open(_DATA / "facts.json", "r", encoding="utf-8") as f:
    facts = json.load(f)
