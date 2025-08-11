import json
from typing import Dict, List

def build_report(process_info: Dict, doc_types: List[Dict], issues: List[Dict]) -> str:
    return json.dumps({
        "process": process_info["process"],
        "documents_uploaded": len(doc_types),
        "required_documents": len(process_info["required_documents"]),
        "missing_document": process_info["missing_document"],
        "issues_found": issues
    }, indent=2, ensure_ascii=False)
