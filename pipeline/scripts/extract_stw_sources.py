"""Audit the supplied PDF and preserve its bibliography separately from runtime navigation content.

Requires pypdf only for this authoring step. Original document text is never loaded as model instructions.
Example: python pipeline/scripts/extract_stw_sources.py --pdf ../STW_Manual_v1.pdf
Optional --text-dir writes each page's extracted text for local inspection.
"""
import argparse
import hashlib
import json
import re
import unicodedata
from pathlib import Path
from urllib.parse import urlparse

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdf", type=Path, required=True)
    parser.add_argument("--text-dir", type=Path)
    args = parser.parse_args()
    catalog = json.loads((ROOT / "backend/app/rules/stw_reference.json").read_text(encoding="utf-8"))
    titles = {t["pdf_page"]: t["title"] for t in catalog["topics"]}
    reader = PdfReader(args.pdf)
    pages, links = [], {}
    if args.text_dir:
        args.text_dir.mkdir(parents=True, exist_ok=True)
    for number, page in enumerate(reader.pages, 1):
        text = page.extract_text() or ""
        if args.text_dir:
            (args.text_dir / f"{number}.txt").write_text(text, encoding="utf-8")
        # Preserve the printed reference block as source data, not current clinical guidance.
        match = re.search(r"\bREFERENCES?\b", text)
        bibliography = text[match.end():] if match else ""
        bibliography = re.split(r"ABBREVIATIONS|This STW has been prepared|Department of Health Research|\n[A-Z][A-Z /()-]{5,}\n", bibliography)[0].strip()
        # Some posters place references above their clinical text. Keep only reference-like lines.
        bibliography = "\n".join(line for line in bibliography.splitlines() if line.strip())[:5000]
        clean = unicodedata.normalize("NFKC", text)
        clean = re.sub(r"https?:\s*/\s*/", lambda m: m.group(0).split(":")[0] + "://", clean)
        urls, incomplete = [], []
        for value in sorted(set(u.rstrip(".,;)") for u in re.findall(r"(?:https?://|www\.)[^\s<>]+", clean))):
            host = urlparse(value if value.startswith("http") else "https://" + value).hostname or ""
            (urls if re.search(r"\.[a-z]{2,}$", host, re.I) else incomplete).append(value)
        for url in urls:
            links.setdefault(url, []).append(number)
        pages.append(dict(pdf_page=number, clinical_topic=titles.get(number), text_characters=len(text),
                          extracted_text_sha256=hashlib.sha256(text.encode("utf-8")).hexdigest(),
                          printed_links=urls, incomplete_link_fragments=incomplete, printed_reference_block=bibliography))
    manifest = dict(source=catalog["source"], source_file_sha256=hashlib.sha256(args.pdf.read_bytes()).hexdigest(),
                    extraction="pypdf; diagram layout can affect reading order; reference blocks and links are unverified printed source data",
                    clinical_topic_count=len(titles), pages=pages,
                    printed_links=[dict(url=url, pdf_pages=numbers) for url, numbers in sorted(links.items())])
    dest = ROOT / "docs/STW_SOURCE_MANIFEST.json"
    dest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Indexed {len(pages)} PDF pages, {len(titles)} clinical topics and {len(links)} printed resource links.")


if __name__ == "__main__":
    main()
