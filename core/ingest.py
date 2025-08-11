from pathlib import Path
from typing import List, Dict
import re
import csv

from sentence_transformers import SentenceTransformer
import chromadb
from langchain.text_splitter import RecursiveCharacterTextSplitter
from pypdf import PdfReader
from docx import Document

REPO_ROOT = Path(__file__).resolve().parents[1]
REF_DIR = REPO_ROOT / "data" / "adgm_refs"
DB_PATH = REPO_ROOT / "data" / "adgm_index"
MANIFEST = REPO_ROOT / "data" / "sources_manifest.csv"

def _read_manifest() -> Dict[str, Dict]:
    """Return a dict keyed by filename prefix -> {category, doc_type, url}"""
    out = {}
    if not MANIFEST.exists():
        return out
    with MANIFEST.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            cat = row["category"].strip()
            dtyp = row["doc_type"].strip()
            url = row["url"].strip()
            prefix = f"{cat}__{dtyp}__".replace(" ", "_")
            out[prefix] = {"category": cat, "doc_type": dtyp, "url": url}
    return out

def _extract_text_pdf(path: Path) -> str:
    reader = PdfReader(str(path))
    text = "\n".join((p.extract_text() or "") for p in reader.pages)
    text = re.sub(r"[ \t]+\n", "\n", text)
    return text

def _extract_text_docx(path: Path) -> str:
    doc = Document(str(path))
    text = "\n".join(p.text for p in doc.paragraphs)
    return re.sub(r"[ \t]+\n", "\n", text)

def load_texts_with_meta() -> List[Dict]:
    manifest = _read_manifest()
    docs = []
    for fp in REF_DIR.iterdir():
        if not fp.is_file():
            continue
        if fp.suffix.lower() not in {".pdf", ".docx"}:
            continue
        text = _extract_text_pdf(fp) if fp.suffix.lower() == ".pdf" else _extract_text_docx(fp)
        meta = {"source_file": fp.name}
        for pref, info in manifest.items():
            if fp.name.startswith(pref.replace(" ", "_")):
                meta.update(info)
                break
        docs.append({"text": text, "meta": meta})
    return docs

def chunk_docs(docs: List[Dict], chunk_size=1200, chunk_overlap=200):
    splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    chunks = []
    for d in docs:
        parts = splitter.split_text(d["text"])
        for i, ch in enumerate(parts):
            chunks.append({
                "id": f"{d['meta'].get('source_file','src')}_{i}",
                "text": ch,
                "meta": d["meta"]
            })
    return chunks

def embed_and_store(chunks: List[Dict]):
    DB_PATH.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(DB_PATH))
    coll = client.get_or_create_collection("adgm")

    model = SentenceTransformer("mixedbread-ai/mxbai-embed-large-v1")
    docs = [c["text"] for c in chunks]
    vecs = model.encode(docs, normalize_embeddings=True).tolist()
    ids = [c["id"] for c in chunks]
    metadatas = chunks_meta = [c["meta"] for c in chunks]

    coll.add(ids=ids, documents=docs, embeddings=vecs, metadatas=chunks_meta)
    return coll.count()

def build_index():
    docs = load_texts_with_meta()
    if not docs:
        raise RuntimeError(f"No references in {REF_DIR}. Run the fetcher first.")
    chunks = chunk_docs(docs)
    n = embed_and_store(chunks)
    return f"Indexed {n} chunks from {len(docs)} source documents."
