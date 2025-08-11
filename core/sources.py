from pathlib import Path
import csv
import time
import shutil
import tempfile
import requests

REPO_ROOT = Path(__file__).resolve().parents[1]
MANIFEST = REPO_ROOT / "data" / "sources_manifest.csv"
RAW_DIR = REPO_ROOT / "data" / "adgm_refs"  

RAW_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": "ADGM-Corporate-Agent/1.0 (+for research; contact: darren@example.com)"
}

def sanitize_filename(name: str) -> str:
    return "".join(c for c in name if c.isalnum() or c in (" ", "-", "_", ".")).strip().replace(" ", "_")

def download(url: str, out_path: Path, timeout=60):
    with requests.get(url, headers=HEADERS, stream=True, timeout=timeout) as r:
        r.raise_for_status()
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    tmp.write(chunk)
            tmp_path = Path(tmp.name)
    shutil.move(str(tmp_path), str(out_path))

def fetch_all(max_retries=2, sleep_between=1.0):
    assert MANIFEST.exists(), f"Manifest not found at {MANIFEST}"
    failures = []
    with MANIFEST.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            url = row["url"].strip()
            doc_type = row["doc_type"].strip()
            category = row["category"].strip()
            suffix = url.split("/")[-1][:70]  
            base = sanitize_filename(f"{category}__{doc_type}__{suffix}")
            out_path = RAW_DIR / base

            if not out_path.suffix:
                if ".pdf" in url.lower():
                    out_path = out_path.with_suffix(".pdf")
                elif ".docx" in url.lower():
                    out_path = out_path.with_suffix(".docx")

            if out_path.exists():
                continue

            ok = False
            for attempt in range(max_retries + 1):
                try:
                    download(url, out_path)
                    ok = True
                    break
                except Exception as e:
                    if attempt == max_retries:
                        failures.append((url, str(e)))
                    time.sleep(sleep_between)

            if ok:
                print(f"Saved: {out_path.name}")
            else:
                print(f"FAILED: {url}")

    if failures:
        print("\nFailures:")
        for u, err in failures:
            print(f"- {u} -> {err}")
    else:
        print("All sources downloaded.")
