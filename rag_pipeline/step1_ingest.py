"""Step 1 - Download the English FastAPI docs and clean them into data/docs.jsonl.

Code-example include directives ({* ../../docs_src/x.py *} and {!../../docs_src/x.py!})
are inlined so chunks contain the actual code the docs show.
"""
import re
import subprocess

from common import DATA, write_json, write_jsonl

REPO_URL = "https://github.com/fastapi/fastapi.git"
REPO = DATA / "fastapi_repo"
DOCS_DIR = REPO / "docs" / "en" / "docs"

# pages that are not technical documentation (or are huge changelogs that would dominate the index)
EXCLUDE = {
    "release-notes.md", "external-links.md", "fastapi-people.md", "management.md",
    "management-tasks.md", "contributing.md", "help-fastapi.md", "newsletter.md",
    "translations.md",
}
EXCLUDE_DIRS = {"reference", "img", "js", "css", "overrides"}
MIN_CHARS = 400

INCLUDE_STAR = re.compile(r"\{\*\s*(\S+)[^*{}]*\*\}")      # {* ../../docs_src/x.py hl[3] *}
INCLUDE_BANG = re.compile(r"\{!>?\s*([^\s!]+)\s*!\}")       # {!../../docs_src/x.py!}
COMMENT = re.compile(r"<!--.*?-->", re.S)
ANCHOR = re.compile(r"\{\s*#[\w-]+\s*\}")
ADMONITION = re.compile(r"^///[ \t]*(\w+)?.*$", re.M)          # /// tip | Title   and closing ///
MK_ADMONITION = re.compile(r"^(?:!!!|\?\?\?)[ \t]*(\w+).*$", re.M)
IMAGE = re.compile(r"!\[[^\]]*\]\([^)]*\)")
HTML_TAG = re.compile(r"</?[a-zA-Z][a-zA-Z0-9]*(?:\s[^>]*)?/?>")
LINK = re.compile(r"\[([^\]]+)\]\([^)]+\)")
BLANKS = re.compile(r"\n{3,}")


def clone():
    if DOCS_DIR.exists():
        print(f"Repo already present at {REPO}")
        return
    print("Cloning FastAPI docs (sparse, shallow)...")
    subprocess.run(["git", "clone", "--depth", "1", "--filter=blob:none", "--sparse",
                    REPO_URL, str(REPO)], check=True)
    subprocess.run(["git", "-C", str(REPO), "sparse-checkout", "set",
                    "docs/en/docs", "docs_src"], check=True)


def load_include(rel, md_path):
    # include paths are relative to docs/en (the mkdocs root), e.g. ../../docs_src/x.py
    for base in (DOCS_DIR.parent, md_path.parent):
        p = (base / rel).resolve()
        if p.is_file():
            return p.read_text(encoding="utf-8").replace("\r\n", "\n").strip()
    return None


def inline_includes(text, md_path):
    def star(m):
        code = load_include(m.group(1), md_path)
        return f"```python\n{code}\n```" if code else ""

    def bang(m):
        return load_include(m.group(1), md_path) or ""

    return INCLUDE_BANG.sub(bang, INCLUDE_STAR.sub(star, text))


def clean(text):
    text = COMMENT.sub("", text)
    text = ANCHOR.sub("", text)
    text = ADMONITION.sub(lambda m: f"{m.group(1).capitalize()}:" if m.group(1) else "", text)
    text = MK_ADMONITION.sub(lambda m: f"{m.group(1).capitalize()}:", text)
    text = IMAGE.sub("", text)
    text = HTML_TAG.sub("", text)   # also strips <font>/<span> noise inside console blocks
    text = LINK.sub(r"\1", text)
    text = BLANKS.sub("\n\n", text)
    return text.strip()


def title_of(text, path):
    m = re.search(r"^#\s+(.+)$", text, re.M)
    return m.group(1).strip() if m else path.stem.replace("-", " ").title()


def main():
    clone()
    commit = subprocess.run(["git", "-C", str(REPO), "rev-parse", "HEAD"],
                            capture_output=True, text=True).stdout.strip()
    docs = []
    for p in sorted(DOCS_DIR.rglob("*.md")):
        rel = p.relative_to(DOCS_DIR)
        if p.name in EXCLUDE or (rel.parts and rel.parts[0] in EXCLUDE_DIRS):
            continue
        raw = p.read_text(encoding="utf-8").replace("\r\n", "\n")
        text = clean(inline_includes(raw, p))
        if len(text) < MIN_CHARS:
            continue
        doc_id = rel.as_posix().removesuffix(".md")
        docs.append({"doc_id": doc_id, "title": title_of(text, p), "text": text})

    write_jsonl(DATA / "docs.jsonl", docs)
    write_json(DATA / "corpus_meta.json", {"source": REPO_URL, "commit": commit, "n_docs": len(docs)})
    print(f"Saved {len(docs)} documents to data/docs.jsonl (fastapi commit {commit[:10]})")


if __name__ == "__main__":
    main()
