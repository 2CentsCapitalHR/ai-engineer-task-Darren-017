import streamlit as st
from pathlib import Path
from core.classify import classify_doc
from core.checklist import detect_process_and_compare
from core.redflags import analyze_document
from core.comments import annotate_docx
from core.summarize import build_report
from core.ingest import build_index
from core.rag import ask_gemini

REPO_ROOT = Path(__file__).resolve().parent

st.set_page_config(page_title="ADGM Document Review", layout="wide")
st.title("ADGM Corporate Agent — ADGM Document Review")

@st.cache_resource
def _ready():
    return True

_ready()

with st.sidebar:
    st.header("Admin")
    st.caption("Run this once (after fetching sources) to build the RAG index.")
    if st.button("Build ADGM RAG Index"):
        try:
            msg = build_index()
            st.success(msg)
        except Exception as e:
            st.error(str(e))

uploaded = st.file_uploader("Upload .docx files", type=["docx"], accept_multiple_files=True)
run_btn = st.button("Run Review")

if run_btn and uploaded:
    outputs_dir = REPO_ROOT / "outputs"
    (outputs_dir / "reviewed").mkdir(parents=True, exist_ok=True)
    (outputs_dir / "reports").mkdir(parents=True, exist_ok=True)

    all_issues = []
    doc_types = []

    for file in uploaded:
        temp_path = REPO_ROOT / "data" / "samples" / file.name
        temp_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path.write_bytes(file.getbuffer())

        dtype = classify_doc(temp_path)
        doc_types.append({"filename": file.name, "type": dtype})

        issues = analyze_document(temp_path, dtype)
        all_issues.extend(issues)

        reviewed_path = outputs_dir / "reviewed" / f"reviewed_{file.name}"
        annotate_docx(temp_path, issues, reviewed_path)

        st.success(f"Reviewed: {file.name}")
        st.download_button(
            "⬇ Download reviewed .docx",
            data=reviewed_path.read_bytes(),
            file_name=reviewed_path.name,
            key=f"dl-{file.name}"
        )

    if all_issues:
        bullets = "\n".join(
            f"- {i.get('document')}: {i.get('section')} — {i.get('issue')} "
            f"(Suggestion: {i.get('suggestion')})"
            for i in all_issues if i.get("issue")
        )
        phrased_overall = ask_gemini(
            "Rewrite these cross-document compliance findings as 5–7 concise, professional bullets for an executive summary.",
            bullets[:8000]  
        )
        if phrased_overall and not phrased_overall.startswith("("):
            all_issues.append({
                "document": "ALL",
                "section": "Summary",
                "issue": "LLM phrased overall review notes",
                "severity": "Info",
                "suggestion": phrased_overall,
                "citations": []
            })

    process_info = detect_process_and_compare(doc_types)
    report = build_report(process_info, doc_types, all_issues)
    report_path = outputs_dir / "reports" / "report.json"
    report_path.write_text(report, encoding="utf-8")

    st.subheader("Checklist Result")
    st.json(process_info)

    st.subheader("Issues Found")
    st.json(all_issues)

    st.download_button("⬇ Download JSON Report", data=report, file_name="report.json")
