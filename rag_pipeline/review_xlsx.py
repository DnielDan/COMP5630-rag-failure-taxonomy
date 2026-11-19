"""Formatted Excel copy of the label-review CSV (CSV can't store wrap/widths).

  python review_xlsx.py export   # labels_for_review.csv  -> labels_for_review.xlsx
  python review_xlsx.py import   # labels_for_review.xlsx -> labels_for_review.csv (human_label_A/B, notes)
"""
import csv
import math
import sys

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.worksheet.datavalidation import DataValidation

from common import RESULTS

CSV = RESULTS / "labels_for_review.csv"
XLSX = RESULTS / "labels_for_review.xlsx"
HUMAN = ["human_label_A", "human_label_B", "final_label", "notes"]
WIDTHS = {
    "system": 13, "qid": 10, "type": 12, "question": 45, "gold_answer": 45, "answer": 55,
    "gold_retrieved": 10, "answer_in_context": 11, "llm_label": 9, "llm_reason": 40,
    "judge_reason": 40, "human_label_A": 11, "human_label_B": 11, "final_label": 11, "notes": 30,
}
ORDER = {"dense": 0, "dense_rerank": 1, "rewrite": 2, "bm25": 3}  # label these first


def read_csv():
    with open(CSV, encoding="utf-8-sig", newline="") as f:
        r = csv.DictReader(f)
        return r.fieldnames, list(r)


def est_lines(text, width):
    chars = max(width * 1.15, 1)  # ~chars per line at Calibri 11
    return sum(max(1, math.ceil(len(part) / chars)) for part in str(text).split("\n"))


def export():
    cols, rows = read_csv()
    rows.sort(key=lambda r: (ORDER.get(r["system"], 9), r["qid"]))
    wb = Workbook()
    ws = wb.active
    ws.title = "labels"
    ws.append(cols)
    for r in rows:
        ws.append([r.get(c, "") for c in cols])

    wrap = Alignment(wrap_text=True, vertical="top")
    head_fill = PatternFill("solid", fgColor="DDE6F0")
    human_fill = PatternFill("solid", fgColor="FFF4CC")
    for i, c in enumerate(cols, 1):
        letter = ws.cell(1, i).column_letter
        ws.column_dimensions[letter].width = WIDTHS.get(c, 15)
        h = ws.cell(1, i)
        h.font = Font(bold=True)
        h.fill = human_fill if c in HUMAN else head_fill
        h.alignment = Alignment(wrap_text=True, vertical="center", horizontal="center")
    ws.row_dimensions[1].height = 32

    for ri in range(2, ws.max_row + 1):
        lines = 1
        for ci, c in enumerate(cols, 1):
            cell = ws.cell(ri, ci)
            cell.alignment = wrap
            if c in HUMAN:
                cell.fill = human_fill
            lines = max(lines, est_lines(cell.value or "", WIDTHS.get(c, 15)))
        ws.row_dimensions[ri].height = min(409, 15 * lines + 4)

    dv = DataValidation(type="list", formula1='"R1,R2,R3,R4,R5,R6,OTHER"', allow_blank=True)
    dv.error = "Use R1-R6 or OTHER"
    ws.add_data_validation(dv)
    for c in ("human_label_A", "human_label_B", "final_label"):
        letter = ws.cell(1, cols.index(c) + 1).column_letter
        dv.add(f"{letter}2:{letter}{ws.max_row}")

    ws.freeze_panes = "D2"
    ws.auto_filter.ref = ws.dimensions
    wb.save(XLSX)
    print(f"wrote {XLSX} ({len(rows)} rows)")


def import_():
    cols, rows = read_csv()
    ws = load_workbook(XLSX, read_only=True).active
    it = ws.iter_rows(values_only=True)
    head = list(next(it))
    got = {}
    for vals in it:
        d = dict(zip(head, vals))
        if d.get("system") and d.get("qid"):
            got[(d["system"], d["qid"])] = d
    n = 0
    for r in rows:
        d = got.get((r["system"], r["qid"]))
        if not d:
            continue
        for c in HUMAN:
            v = "" if d.get(c) is None else str(d[c]).strip()
            if c != "notes":
                v = v.upper()
            if v != r.get(c, ""):
                r[c] = v
                n += 1
    with open(CSV, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)
    filled = sum(1 for r in rows if r["human_label_A"])
    print(f"updated {n} cells; human_label_A filled on {filled}/{len(rows)} rows")


if __name__ == "__main__":
    {"export": export, "import": import_}[sys.argv[1] if len(sys.argv) > 1 else "export"]()
