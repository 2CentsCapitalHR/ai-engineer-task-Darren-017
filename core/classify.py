from pathlib import Path
from docx import Document

KEYWORDS = {
    "Articles of Association": ["articles of association", "aoa"],
    "Memorandum of Association": ["memorandum of association", "moa"],
    "Board Resolution": ["board resolution", "board of directors"],
    "Shareholder Resolution": ["shareholder resolution", "extraordinary general meeting", "egm"],
    "Register of Members": ["register of members"],
    "Register of Directors": ["register of directors"],
    "UBO Declaration": ["ultimate beneficial owner", "ubo"],
    "Incorporation Application Form": ["incorporation application form", "application for incorporation"],
    "Change of Registered Address Notice": ["change of registered address"]
}

def classify_doc(path: Path) -> str:
    text = extract_text_quick(path).lower()
    for label, cues in KEYWORDS.items():
        if any(cue in text for cue in cues):
            return label
    return "Unknown"

def extract_text_quick(path: Path) -> str:
    try:
        doc = Document(str(path))
        return "\n".join(p.text for p in doc.paragraphs)
    except Exception:
        return ""
