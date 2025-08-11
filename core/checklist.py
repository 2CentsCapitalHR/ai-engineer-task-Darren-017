from typing import List, Dict
from pathlib import Path
import json

REPO_ROOT = Path(__file__).resolve().parents[1]
CHECKLIST_DIR = REPO_ROOT / "data" / "checklists"

def load_checklist(process_name: str) -> Dict:
    mapping = {
        "Company Incorporation": "incorporation.json"
    }
    fname = mapping.get(process_name)
    if not fname:
        return {"process": "Unknown", "required_documents": []}
    return json.loads((CHECKLIST_DIR / fname).read_text(encoding="utf-8"))

def detect_process(detected_labels: set) -> str:
    if "Articles of Association" in detected_labels or "Memorandum of Association" in detected_labels:
        return "Company Incorporation"
    return "Unknown"

def detect_process_and_compare(detected_docs: List[Dict]) -> Dict:
    labels = {d["type"] for d in detected_docs}
    process = detect_process(labels)
    checklist = load_checklist(process)
    required = checklist.get("required_documents", [])
    missing = [r for r in required if r not in labels]
    return {
        "process": process,
        "required_documents": required,
        "documents_uploaded": list(labels),
        "missing_document": missing
    }
