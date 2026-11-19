"""Step 6 - Tables, figures and example failures for the slides.

Failure labels: final_label (adjudicated) > human_label_A > llm_label.

Outputs (results/):
  summary.md / summary.csv         main results table + failure counts + label agreement
  examples.md                      one real example per failure type (for the taxonomy slide)
  figures/fig1_accuracy_recall.png
  figures/fig2_failure_distribution.png   <- the headline before/after chart
  figures/fig3_type_x_failure.png
  figures/fig4_accuracy_by_type.png
"""
import csv
import textwrap
from collections import Counter

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import matplotlib.ticker  # noqa: E402,F401
import numpy as np  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap  # noqa: E402

from common import DATA, FAILURE_LABELS, FIG, QUESTION_MIX, RESULTS, read_json, read_jsonl  # noqa: E402
from retrieval import SYSTEMS  # noqa: E402

BASELINE, MITIGATION = "dense", "dense_rerank"   # the "before" and "after" for the headline chart
SYSTEM_NAMES = {"bm25": "BM25 (classic)", "dense": "Dense RAG (standard)",
                "dense_rerank": "Dense + reranker", "rewrite": "Query rewrite + reranker"}
TYPE_NAMES = {"lookup": "Lookup", "multi_hop": "Multi-hop", "unanswerable": "Unanswerable",
              "ambiguous": "Ambiguous", "conflicting": "Conflicting"}

# ---- palette (validated categorical order; one color per system, fixed by entity, never by rank)
SURFACE, INK, INK2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
SYSTEM_COLORS = {"bm25": "#2a78d6", "dense": "#eb6834", "dense_rerank": "#1baf7a", "rewrite": "#eda100"}
SEQ = LinearSegmentedColormap.from_list("seq_blue", ["#f1f6fd", "#9cc3f0", "#2a78d6", "#0d3b7a"])

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "axes.edgecolor": GRID, "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
    "text.color": INK, "font.size": 12, "axes.titlesize": 15, "axes.titleweight": "bold",
    "axes.titlelocation": "left", "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "axes.grid.axis": "y", "grid.color": GRID, "grid.linewidth": 0.8,
    "axes.axisbelow": True, "legend.frameon": False,
})


def kappa(a, b):
    labels = sorted(set(a) | set(b))
    n = len(a)
    if n == 0:
        return None
    po = sum(x == y for x, y in zip(a, b)) / n
    ca, cb = Counter(a), Counter(b)
    pe = sum(ca[l] * cb[l] for l in labels) / (n * n)
    return 1.0 if pe == 1 else (po - pe) / (1 - pe)


def load():
    rows = read_jsonl(RESULTS / "judged.jsonl")
    human = {}
    review = RESULTS / "labels_for_review.csv"
    if review.exists():
        with open(review, encoding="utf-8-sig", newline="") as f:
            for r in csv.DictReader(f):
                human[(r["system"], r["qid"])] = r
    for r in rows:
        h = human.get((r["system"], r["qid"]), {})
        r["human_A"] = (h.get("human_label_A") or "").strip().upper()
        r["human_B"] = (h.get("human_label_B") or "").strip().upper()
        r["final"] = (h.get("final_label") or "").strip().upper()   # adjudicated A/B consensus
        r["label"] = "" if r["correct"] else (r["final"] or r["human_A"] or r["llm_label"] or "OTHER")
    return rows, human


def apply_corrections(rows):
    """data/corrections.json: drop bad-gold questions; flip judge errors (annotators: answer correct)."""
    p = DATA / "corrections.json"
    if not p.exists():
        return rows, None
    c = read_json(p)
    drop = set(c.get("drop_questions", {}))
    flip = {(o["system"], o["qid"]) for o in c.get("judge_overrides", [])}
    out = []
    for r in rows:
        if r["qid"] in drop:
            continue
        r = dict(r)
        if (r["system"], r["qid"]) in flip and not r["correct"]:
            r["correct"], r["label"], r["judge_overridden"] = True, "", True
        out.append(r)
    return out, {"dropped": sorted(drop), "flipped": len(flip)}


def bar_labels(ax, bars, fmt):
    for b in bars:
        h = b.get_height()
        ax.annotate(fmt(h), (b.get_x() + b.get_width() / 2, h), xytext=(0, 3), textcoords="offset points",
                    ha="center", va="bottom", fontsize=10, color=INK2)


def tick(label):
    """'R3' -> 'R3\\nRight chunk,\\nwrong answer' so neighbouring tick labels never collide."""
    return f"{label}\n" + textwrap.fill(FAILURE_LABELS.get(label, "Other"), 14)


def top_legend(ax, n):
    """Legend in its own row between title and plot, so it can never cover a bar."""
    ax.legend(ncol=n, loc="lower left", bbox_to_anchor=(0, 1.0), fontsize=10, handlelength=1.2,
              borderaxespad=0.2)


def save(fig, name):
    fig.tight_layout()
    fig.savefig(FIG / name, dpi=200)
    plt.close(fig)


def main():
    raw, _ = load()
    rows, corr = apply_corrections(raw)
    systems = [s for s in SYSTEMS if any(r["system"] == s for r in rows)]
    raw_acc = {s: np.mean([r["correct"] for r in raw if r["system"] == s]) for s in systems}
    raw_fail = {s: sum(not r["correct"] for r in raw if r["system"] == s) for s in systems}
    raw_n = sum(1 for r in raw if r["system"] == systems[0])
    labels = list(FAILURE_LABELS) + (["OTHER"] if any(r["label"] == "OTHER" for r in rows) else [])
    types = [t for t in QUESTION_MIX if any(r["type"] == t for r in rows)]

    # ------------------------------------------------------------ metrics
    stats = {}
    for s in systems:
        rs = [r for r in rows if r["system"] == s]
        rec = [r["recall_at_k"] for r in rs if r["recall_at_k"] is not None]
        hit = [r["hit_at_k"] for r in rs if r["hit_at_k"] is not None]
        stats[s] = {
            "n": len(rs),
            "accuracy": np.mean([r["correct"] for r in rs]),
            "recall@5": np.mean(rec) if rec else float("nan"),
            "hit@5": np.mean(hit) if hit else float("nan"),
            "failures": sum(not r["correct"] for r in rs),
            "by_type": {t: np.mean([r["correct"] for r in rs if r["type"] == t]) for t in types},
            "labels": Counter(r["label"] for r in rs if not r["correct"]),
        }

    # ------------------------------------------------------------ agreement (on every judged failure, pre-correction)
    both = [r for r in raw if not r["correct"] and r["human_A"] and r["human_B"]]
    a_llm = [r for r in raw if not r["correct"] and r["human_A"]]
    k_ab = kappa([r["human_A"] for r in both], [r["human_B"] for r in both])
    k_al = kappa([r["human_A"] for r in a_llm], [r["llm_label"] for r in a_llm])
    fin = [r for r in raw if not r["correct"] and r["final"]]
    k_fl = kappa([r["final"] for r in fin], [r["llm_label"] for r in fin])
    k_bl = kappa([r["human_B"] for r in both], [r["llm_label"] for r in both])

    # ------------------------------------------------------------ summary tables
    md = ["# Results summary\n", f"Questions: {stats[systems[0]]['n']}  ·  k = 5\n",
          "## Main results\n", "| System | Accuracy | Recall@5 | Hit@5 | # Failures |", "|---|---|---|---|---|"]
    for s in systems:
        st = stats[s]
        md.append(f"| {SYSTEM_NAMES[s]} | {st['accuracy']:.1%} | {st['recall@5']:.1%} | {st['hit@5']:.1%} | {st['failures']} |")
    md += ["\n## Accuracy by question type\n", "| System | " + " | ".join(TYPE_NAMES[t] for t in types) + " |",
           "|---|" + "---|" * len(types)]
    for s in systems:
        md.append(f"| {SYSTEM_NAMES[s]} | " + " | ".join(f"{stats[s]['by_type'][t]:.0%}" for t in types) + " |")
    md += ["\n## Failure distribution (counts)\n", "| System | " + " | ".join(labels) + " |",
           "|---|" + "---|" * len(labels)]
    for s in systems:
        md.append(f"| {SYSTEM_NAMES[s]} | " + " | ".join(str(stats[s]['labels'].get(l, 0)) for l in labels) + " |")
    md += ["\n## Label agreement\n",
           f"- Human A vs Human B: kappa = {k_ab:.2f} on {len(both)} failures" if k_ab is not None
           else "- Human A vs Human B: (no doubly-labelled rows yet)",
           f"- Human A vs LLM pre-label: kappa = {k_al:.2f} on {len(a_llm)} failures" if k_al is not None
           else "- Human A vs LLM pre-label: (no human labels yet - figures use LLM pre-labels)"]
    if k_bl is not None:
        md.append(f"- Human B vs LLM pre-label: kappa = {k_bl:.2f} on {len(both)} failures")
    if k_fl is not None:
        n_dis = sum(r["human_A"] != r["human_B"] for r in both)
        md.append(f"- Final (adjudicated) label vs LLM pre-label: kappa = {k_fl:.2f} on {len(fin)} failures "
                  f"({n_dis} A/B disagreements resolved by checking the retrieved passages)")
    n_human = sum(1 for r in raw if not r["correct"] and r["human_A"])
    n_final = len(fin)
    n_fail = sum(1 for r in raw if not r["correct"])
    md.append(f"- Failures with a human label: {n_human}/{n_fail}; with a final label: {n_final}/{n_fail}")
    md.append("- Figures and failure counts use final_label (fallback: human_label_A, then llm_label)")
    if corr:
        md += ["\n## Corrections (data/corrections.json)\n",
               f"- Dropped {len(corr['dropped'])} bad-gold questions: {', '.join(corr['dropped'])} "
               f"({raw_n} -> {stats[systems[0]]['n']} questions)",
               f"- {corr['flipped']} answers the LLM judge marked wrong were judged correct by both annotators "
               "and counted as correct",
               "\n| System | Accuracy (LLM judge, raw) | Accuracy (corrected) | Failures raw -> corrected |",
               "|---|---|---|---|"]
        for s in systems:
            md.append(f"| {SYSTEM_NAMES[s]} | {raw_acc[s]:.1%} | {stats[s]['accuracy']:.1%} | "
                      f"{raw_fail[s]} -> {stats[s]['failures']} |")
    (RESULTS / "summary.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    with open(RESULTS / "summary.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["system", "accuracy", "recall@5", "hit@5", "failures"] + [f"acc_{t}" for t in types] + labels)
        for s in systems:
            st = stats[s]
            w.writerow([s, f"{st['accuracy']:.4f}", f"{st['recall@5']:.4f}", f"{st['hit@5']:.4f}", st["failures"]]
                       + [f"{st['by_type'][t]:.4f}" for t in types] + [st["labels"].get(l, 0) for l in labels])
    print("\n".join(md))

    # ------------------------------------------------------------ fig 1: accuracy & recall (two panels, one axis each)
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.6))
    x = np.arange(len(systems))
    for ax, key, title in [(axes[0], "accuracy", "End-to-end accuracy"), (axes[1], "recall@5", "Retrieval recall@5")]:
        bars = ax.bar(x, [stats[s][key] for s in systems], width=0.6,
                      color=[SYSTEM_COLORS[s] for s in systems], edgecolor=SURFACE, linewidth=2)
        bar_labels(ax, bars, lambda v: f"{v:.0%}")
        ax.set_xticks(x, [SYSTEM_NAMES[s].replace(" (", "\n(").replace(" + ", "\n+ ") for s in systems], fontsize=10)
        ax.set_ylim(0, 1.08)
        ax.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0))
        ax.set_title(title)
    save(fig, "fig1_accuracy_recall.png")

    # ------------------------------------------------------------ fig 2: failure distribution per system
    fig, ax = plt.subplots(figsize=(12, 5))
    xl = np.arange(len(labels))
    w = 0.8 / len(systems)
    for i, s in enumerate(systems):
        vals = [stats[s]["labels"].get(l, 0) for l in labels]
        bars = ax.bar(xl + (i - (len(systems) - 1) / 2) * w, vals, width=w, color=SYSTEM_COLORS[s],
                      edgecolor=SURFACE, linewidth=2, label=SYSTEM_NAMES[s])
        if s in (BASELINE, MITIGATION):
            bar_labels(ax, [b for b in bars if b.get_height() > 0], lambda v: f"{int(v)}")
    ax.set_xticks(xl, [tick(l) for l in labels], fontsize=10)
    ax.set_ylabel("# wrong answers")
    ax.set_title("Where each system fails (failure type counts)", pad=34)
    ax.margins(y=0.12)
    top_legend(ax, len(systems))
    ax.yaxis.set_major_locator(matplotlib.ticker.MaxNLocator(integer=True))
    save(fig, "fig2_failure_distribution.png")

    # ------------------------------------------------------------ fig 3: question type x failure type heatmap (baseline)
    base = BASELINE if BASELINE in systems else systems[0]
    M = np.array([[sum(1 for r in rows if r["system"] == base and r["type"] == t and r["label"] == l)
                   for l in labels] for t in types])
    fig, ax = plt.subplots(figsize=(10, 4.8))
    ax.grid(False)
    im = ax.imshow(M, cmap=SEQ, aspect="auto", vmin=0)
    for i in range(len(types)):
        for j in range(len(labels)):
            if M[i, j]:
                ax.text(j, i, str(M[i, j]), ha="center", va="center", fontsize=11,
                        color="white" if M[i, j] > M.max() * 0.55 else INK)
    ax.set_xticks(range(len(labels)), [tick(l) for l in labels], fontsize=9)
    ax.set_yticks(range(len(types)), [TYPE_NAMES[t] for t in types])
    ax.set_title(f"Which question types cause which failures — {SYSTEM_NAMES[base]}")
    for sp in ax.spines.values():
        sp.set_visible(False)
    fig.colorbar(im, ax=ax, fraction=0.03, pad=0.02).outline.set_visible(False)
    save(fig, "fig3_type_x_failure.png")

    # ------------------------------------------------------------ fig 4: accuracy by question type
    fig, ax = plt.subplots(figsize=(12, 4.8))
    xt = np.arange(len(types))
    for i, s in enumerate(systems):
        ax.bar(xt + (i - (len(systems) - 1) / 2) * w, [stats[s]["by_type"][t] for t in types], width=w,
               color=SYSTEM_COLORS[s], edgecolor=SURFACE, linewidth=2, label=SYSTEM_NAMES[s])
    ax.set_xticks(xt, [TYPE_NAMES[t] for t in types])
    ax.set_ylim(0, 1.12)
    ax.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0))
    ax.set_title("Accuracy by question type", pad=34)
    top_legend(ax, len(systems))
    save(fig, "fig4_accuracy_by_type.png")

    # ------------------------------------------------------------ examples per failure type
    questions = {q["qid"]: q for q in read_json(DATA / "questions.json")}
    from retrieval import Retriever
    r = Retriever()
    ex = ["# One real example per failure type\n",
          f"Drawn from **{SYSTEM_NAMES[base]}** (falls back to other systems). Human-labelled rows preferred.\n"]
    for l in labels:
        cands = sorted([x for x in rows if x["label"] == l],
                       key=lambda x: (x["system"] != base, not x["human_A"], len(x["answer"])))
        ex.append(f"## {l} · {FAILURE_LABELS.get(l, 'Other')}  ({sum(1 for x in rows if x['label'] == l)} total)\n")
        if not cands:
            ex.append("_No examples._\n")
            continue
        x = cands[0]
        q = questions[x["qid"]]
        ex += [f"- **System:** {SYSTEM_NAMES[x['system']]}  ·  **Type:** {TYPE_NAMES[x['type']]}  ·  `{x['qid']}`",
               f"- **Question:** {x['question']}",
               f"- **Gold answer:** {q['gold_answer']}",
               f"- **System answer:** {x['answer']}",
               f"- **Gold chunk retrieved:** {x['gold_hits']}/{x['n_gold']}",
               "- **Retrieved sections:** " + "; ".join(r.by_id[c]["section"] for c in x["retrieved"]),
               f"- **Why ({'human' if x['human_A'] else 'LLM'} label):** {x['label_reason'] or x['judge_reason']}\n"]
    (RESULTS / "examples.md").write_text("\n".join(ex), encoding="utf-8")
    print(f"\nFigures in {FIG}\nExamples in {RESULTS / 'examples.md'}")


if __name__ == "__main__":
    main()
