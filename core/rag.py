import os
from typing import List, Dict
from pathlib import Path
from dotenv import load_dotenv
import chromadb
from sentence_transformers import SentenceTransformer
import google.generativeai as genai

REPO_ROOT = Path(__file__).resolve().parents[1]
DB_PATH = REPO_ROOT / "data" / "adgm_index"

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
ENABLE_LLM = os.getenv("ENABLE_LLM_SUMMARY", "true").lower() == "true"

if api_key:
    genai.configure(api_key=api_key)

def _choose_model() -> str:
    """
    Prefer a low-cost, free-tier friendly model.
    We'll try to list models; if that fails, default to flash.
    """
    try:
        models = list(genai.list_models())
        generative = [m.name for m in models if "generateContent" in getattr(m, "supported_generation_methods", [])]
        for p in ["gemini-1.5-flash", "gemini-1.5-pro"]:
            if p in generative:
                return p
        return generative[0] if generative else "gemini-1.5-flash"
    except Exception:
        return "gemini-1.5-flash"

def _collection():
    client = chromadb.PersistentClient(path=str(DB_PATH))
    return client.get_or_create_collection("adgm")

def retrieve(query: str, top_k=5) -> List[Dict]:
    """
    Vector search into the ADGM reference index. Returns text + rich metadata for citations.
    """
    coll = _collection()
    model = SentenceTransformer("mixedbread-ai/mxbai-embed-large-v1")
    q_emb = model.encode([query], normalize_embeddings=True).tolist()

    # NOTE: chromadb build does not accept "ids" in include
    res = coll.query(
        query_embeddings=q_emb,
        n_results=top_k,
        include=["documents", "metadatas", "distances"]
    )

    out: List[Dict] = []
    if not res or not res.get("documents") or not res["documents"]:
        return out

    n_hits = len(res["documents"][0])
    for i in range(n_hits):
        md = res["metadatas"][0][i] if res.get("metadatas") else {}
        out.append({
            "text": res["documents"][0][i],
            "source_file": md.get("source_file", ""),
            "category": md.get("category", ""),
            "doc_type": md.get("doc_type", ""),
            "url": md.get("url", ""),
            "score": float(res["distances"][0][i]) if res.get("distances") else None,
        })
    return out

def ask_gemini(system_prompt: str, user_prompt: str) -> str:
    """
    Quota-safe wrapper for Gemini. Returns a benign string if:
    - LLM is disabled,
    - no API key,
    - or quota/rate limits are hit.
    """
    if not ENABLE_LLM:
        return "(LLM disabled by configuration)"
    if not api_key:
        return "(Gemini not configured)"

    model_name = _choose_model()
    if model_name != "gemini-1.5-flash":
        model_name = "gemini-1.5-flash"

    try:
        model = genai.GenerativeModel(model_name)
        prompt = (system_prompt + "\n\n" + user_prompt).strip()
        if len(prompt) > 8000:
            prompt = prompt[:8000]
        resp = model.generate_content(prompt)
        return getattr(resp, "text", "").strip() or "(No response)"
    except Exception as e:
        msg = str(e)
        if "ResourceExhausted" in msg or "429" in msg or "rate" in msg.lower():
            return "(LLM summary skipped due to quota limits)"
        return f"(LLM error: {msg[:200]})"
