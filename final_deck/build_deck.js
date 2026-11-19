// Builds RAG_Final_Presentation.pptx from rag_pipeline/results/summary.csv.
// Run from anywhere:  node final_deck/build_deck.js
const path = require("path");
const fs = require("fs");
const pptxgen = require("pptxgenjs");
const { applyTheme } = require("./apply_theme.js"); // copied from the pptx skill

const ROOT = path.resolve(__dirname, "..");
const OUT = path.join(ROOT, "RAG_Final_Presentation.pptx");

// ------------------------------------------------------------------ data
const csv = fs.readFileSync(path.join(ROOT, "rag_pipeline", "results", "summary.csv"), "utf8").trim().split(/\r?\n/);
const head = csv[0].split(",");
const S = {};
for (const line of csv.slice(1)) {
  const v = line.split(",");
  S[v[0]] = Object.fromEntries(head.map((h, i) => [h, i ? Number(v[i]) : v[i]]));
}
const SYS = ["bm25", "dense", "dense_rerank", "rewrite"];
const SYS_NAME = { bm25: "BM25 (classic)", dense: "Dense (standard)", dense_rerank: "Dense + reranker", rewrite: "Query rewrite + reranker" };
const SYS_COLOR = { bm25: "2A78D6", dense: "EB6834", dense_rerank: "1BAF7A", rewrite: "EDA100" };
const pct = (x) => Math.round(x * 1000) / 10;
const totals = (l) => SYS.reduce((a, s) => a + S[s][l], 0);

// ------------------------------------------------------------------ theme
const THEME = {
  name: "RAG Final",
  headFontFace: "Georgia",
  bodyFontFace: "Calibri",
  colors: {
    dk1: "1C2430", lt1: "FFFFFF", dk2: "5B6472", lt2: "F7F8FA",
    accent1: "C9711F", accent2: "2A78D6", accent3: "EB6834", accent4: "1BAF7A",
    accent5: "EDA100", accent6: "8B93A1", hlink: "2A78D6", folHlink: "5B6472",
  },
};
const HEX = { ink: "1C2430", body: "5B6472", muted: "8B93A1", grid: "DDE1E7", orange: "C9711F" };

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13.33 x 7.5
pres.title = "Where RAG Actually Breaks";
pres.author = "Daniel Choi, Henry Naingshwe";
pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
const C = pres.SchemeColor;

// ------------------------------------------------------------------ layouts
pres.defineSlideMaster({
  title: "CONTENT",
  background: { color: C.background2 },
  objects: [
    { placeholder: { options: { name: "eyebrow", type: "body", x: 0.6, y: 0.38, w: 9, h: 0.35, fontFace: "Consolas", fontSize: 12, bold: true, color: C.accent1, charSpacing: 2, margin: 0, valign: "top" }, text: "" } },
    { placeholder: { options: { name: "title", type: "title", x: 0.6, y: 0.72, w: 12.1, h: 0.95, fontSize: 30, bold: false, color: C.text1, margin: 0, valign: "top", align: "left" }, text: "" } },
    { text: { text: "Where RAG Actually Breaks · COMP 5630", options: { x: 0.6, y: 7.02, w: 6, h: 0.3, fontSize: 10, color: C.accent6, margin: 0 } } },
  ],
  slideNumber: { x: 12.23, y: 7.02, w: 0.5, h: 0.3, fontSize: 10, color: C.accent6, align: "right" },
});
pres.defineSlideMaster({
  title: "DARK",
  background: { color: C.text1 },
  objects: [
    { placeholder: { options: { name: "eyebrow", type: "body", x: 0.8, y: 0.7, w: 11, h: 0.35, fontFace: "Consolas", fontSize: 12, bold: true, color: C.accent1, charSpacing: 2, margin: 0, valign: "top" }, text: "" } },
    { placeholder: { options: { name: "title", type: "title", x: 0.8, y: 1.15, w: 11.7, h: 1.4, fontSize: 32, color: C.background1, margin: 0, valign: "top", align: "left" }, text: "" } },
  ],
});
pres.defineSlideMaster({
  title: "DARK_TITLE",
  background: { color: C.text1 },
  objects: [
    { placeholder: { options: { name: "eyebrow", type: "body", x: 0.8, y: 0.7, w: 11, h: 0.35, fontFace: "Consolas", fontSize: 12, bold: true, color: C.accent1, charSpacing: 2, margin: 0, valign: "top" }, text: "" } },
    { placeholder: { options: { name: "title", type: "title", x: 0.8, y: 2.3, w: 11.7, h: 1.3, fontSize: 54, color: C.background1, margin: 0, valign: "bottom", align: "left" }, text: "" } },
  ],
});

// helpers ------------------------------------------------------------
function content(section, eyebrow, title) {
  const s = pres.addSlide({ masterName: "CONTENT", sectionTitle: section });
  s.addText(eyebrow, { placeholder: "eyebrow" });
  s.addText(title, { placeholder: "title" });
  return s;
}
function card(s, x, y, w, h, heading, text, opts = {}) {
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x, y, w, h, rectRadius: 0.08, fill: { color: opts.fill || C.background1 },
    line: { color: HEX.grid, width: 1 }, objectName: `card ${heading}`,
  });
  s.addText([
    { text: heading, options: { fontFace: "Georgia", fontSize: opts.hSize || 17, bold: true, color: opts.hColor || C.text1, breakLine: true } },
    { text: text, options: { fontSize: opts.tSize || 14, color: C.text2 } },
  ], { x: x + 0.25, y: y + 0.2, w: w - 0.5, h: h - 0.4, valign: "top", paraSpaceAfter: 6, margin: 0, isTextBox: true });
}
const chartText = { catAxisLabelFontFace: "+mn-lt", valAxisLabelFontFace: "+mn-lt", legendFontFace: "+mn-lt", dataLabelFontFace: "+mn-lt", titleFontFace: "+mn-lt" };
const chartFrame = {
  catAxisLabelColor: HEX.body, valAxisLabelColor: HEX.muted, catAxisLabelFontSize: 12, valAxisLabelFontSize: 11,
  valGridLine: { color: HEX.grid, size: 0.75 }, catGridLine: { style: "none" },
  dataLabelColor: HEX.ink, dataLabelFontSize: 11, legendFontSize: 12, legendColor: HEX.body,
  catAxisLineShow: true, catAxisLineColor: HEX.grid, valAxisLineShow: false,
};

// ================================================================== 1 cover
pres.addSection({ title: "Introduction" });
{
  const s = pres.addSlide({ masterName: "DARK_TITLE", sectionTitle: "Introduction" });
  s.addText("FINAL PROJECT PRESENTATION · COMP 5630", { placeholder: "eyebrow" });
  s.addText("Where RAG Actually Breaks", { placeholder: "title" });
  s.addText("A human-labeled failure taxonomy for retrieval-augmented QA over the FastAPI documentation",
    { x: 0.8, y: 3.75, w: 9.5, h: 1.0, fontSize: 20, color: C.accent6, margin: 0, valign: "top", isTextBox: true });
  s.addText("Daniel Choi · Henry Naingshwe  ·  November 19, 2026",
    { x: 0.8, y: 6.3, w: 9, h: 0.4, fontSize: 14, color: C.background2, margin: 0, isTextBox: true });
  s.addNotes("Hi, we’re Daniel and Henry. Our project asks a simple question: when a retrieval-augmented QA system gets an answer wrong, why? Not how often — which step broke, and on which kinds of questions.");
}

// ================================================================== 2 motivation
{
  const s = content("Introduction", "01 · MOTIVATION", "An accuracy score says how often RAG fails, not why");
  const items = [
    ["Retrieval missed it", "The right passage never reaches the model.", "Fix: better retrieval"],
    ["Retrieved, then ignored", "The passage is there, but the model says “I don’t know.”", "Fix: prompting"],
    ["Read it, got it wrong", "The model uses the right passage and still answers wrong.", "Fix: generation"],
  ];
  items.forEach(([h, t, f], i) => {
    const x = 0.6 + i * 4.1;
    card(s, x, 2.0, 3.8, 1.9, h, t);
    s.addText(f, { x: x + 0.25, y: 3.3, w: 3.3, h: 0.4, fontSize: 13, bold: true, color: C.accent1, margin: 0, isTextBox: true });
  });
  s.addText([
    { text: "Each failure needs a different fix. ", options: { bold: true, color: C.text1 } },
    { text: "So we measure which failure happens, on which kind of question, and whether the standard fixes target it.", options: { color: C.text2 } },
  ], { x: 0.6, y: 4.45, w: 12.1, h: 1.0, fontSize: 20, margin: 0, valign: "top", isTextBox: true });
  s.addNotes("Most RAG evaluations report one accuracy number. But a wrong answer can come from three very different places: retrieval missed the passage, the model ignored it, or the model misread it. Each needs a different fix, so one number can’t tell you what to fix. That’s the pain point we target.");
}

// ================================================================== 3 related work
{
  const s = content("Introduction", "02 · RELATED WORK", "Prior work scores RAG, but rarely explains its failures");
  const H = (t) => ({ text: t, options: { bold: true, color: C.background1, fill: { color: C.text1 } } });
  const rows = [
    [H("Work"), H("What it does"), H("What it leaves open")],
    ["RAG (Lewis et al., 2020)", "Retrieve, then generate", "Reports end-to-end accuracy only"],
    ["BM25 (Robertson & Zaragoza, 2009); DPR (Karpukhin et al., 2020)", "Sparse vs. dense retrieval", "Retrieval metrics, not answer failures"],
    ["BERT reranking (Nogueira & Cho, 2019)", "Re-score the top candidates", "Assumes retrieval is the bottleneck"],
    ["Query rewriting (Ma et al., 2023)", "An LLM rewrites the query", "Judged on accuracy alone"],
    ["RAGAS (Es et al., 2023); LLM-as-judge (Zheng et al., 2023)", "Automatic scoring with an LLM", "How far can the judge be trusted?"],
    ["Seven Failure Points (Barnett et al., 2024)", "Failure catalog from case studies", "Qualitative; no counts by question type"],
  ];
  s.addTable(rows, {
    x: 0.6, y: 1.85, w: 12.1, colW: [5.0, 3.4, 3.7], fontSize: 13, color: C.text1,
    border: { type: "solid", pt: 0.75, color: HEX.grid }, fill: { color: C.background1 },
    rowH: 0.5, valign: "middle", margin: [4, 8, 4, 8],
  });
  s.addText([
    { text: "Our gap: ", options: { bold: true, color: C.accent1 } },
    { text: "count failure types per question type, with two human annotators, and test whether mitigations move them.", options: { color: C.text1 } },
  ], { x: 0.6, y: 5.85, w: 12.1, h: 0.7, fontSize: 17, margin: 0, valign: "top", isTextBox: true });
  s.addNotes("RAG, BM25, dense retrieval, rerankers and query rewriting are the building blocks we compare. RAGAS and LLM-as-judge automate scoring but don’t tell you whether to trust the judge. Barnett et al. catalog seven failure points from industry case studies — the closest work — but it’s qualitative. We add counts, per question type, with human labels and an agreement measure.");
}

// ================================================================== 4 approach
pres.addSection({ title: "Method" });
{
  const s = content("Method", "03 · APPROACH", "Build it, break it, label why, test the fixes");
  const steps = [
    ["Corpus", "FastAPI docs: 121 pages, 737 chunks of ~400 tokens"],
    ["Retrieve", "4 systems, top-5 passages each"],
    ["Answer", "GPT-4o-mini, must cite passages or say “I don’t know”"],
    ["Judge", "GPT-4o grades each answer and pre-labels failures"],
    ["Label", "2 humans label every failure R1–R6, then adjudicate"],
  ];
  const w = 2.12, gap = 0.37;
  steps.forEach(([h, t], i) => {
    const x = 0.6 + i * (w + gap);
    const human = i === 4;
    s.addShape(pres.shapes.OVAL, { x: x + 0.2, y: 2.05, w: 0.6, h: 0.6, fill: { color: human ? C.accent1 : C.text1 }, line: { type: "none" }, objectName: `step ${i + 1} badge` });
    s.addText(String(i + 1), { x: x + 0.2, y: 2.05, w: 0.6, h: 0.6, fontFace: "Georgia", fontSize: 18, bold: true, color: C.background1, align: "center", valign: "middle", margin: 0, isTextBox: true });
    card(s, x, 2.85, w, 1.75, h, t, { tSize: 13, hSize: 16 });
    if (i < 4) s.addText("→", { x: x + w, y: 3.6, w: gap, h: 0.5, fontSize: 20, color: C.accent6, align: "center", margin: 0, isTextBox: true });
  });
  s.addText([
    { text: "What’s new: ", options: { bold: true, color: C.accent1 } },
    { text: "a stress-test question set × a six-type failure taxonomy × classic and newest retrieval, with failures diagnosed by humans rather than a score.", options: { color: C.text1 } },
  ], { x: 0.6, y: 5.1, w: 12.1, h: 0.9, fontSize: 17, margin: 0, valign: "top", isTextBox: true });
  s.addNotes("Our pipeline: we indexed the FastAPI docs, retrieved with four systems, and had GPT-4o-mini answer with citations or say I don’t know. GPT-4o graded every answer and pre-labeled each failure. Then both of us labeled every failure independently and resolved disagreements by checking the retrieved passages. Every LLM call is cached, so the whole thing is reproducible.");
}

// ================================================================== 5 setup
{
  const s = content("Method", "04 · SETUP & METRICS", "Four retrieval systems, 113 stress-test questions");
  const H = (t) => ({ text: t, options: { bold: true, color: C.background1, fill: { color: C.text1 } } });
  s.addTable([
    [H("System"), H("Role"), H("How it retrieves")],
    ["BM25", "Classic baseline", "Keyword matching (Okapi BM25)"],
    ["Dense", "Standard RAG", "MiniLM embeddings + FAISS"],
    ["Dense + reranker", "Newest", "Top-20 → cross-encoder → top-5"],
    ["Query rewrite", "Mitigation 2", "LLM rewrites query, then rerank"],
  ], { x: 0.6, y: 1.85, w: 6.7, colW: [1.8, 1.7, 3.2], fontSize: 13, color: C.text1, border: { type: "solid", pt: 0.75, color: HEX.grid }, fill: { color: C.background1 }, rowH: 0.5, valign: "middle", margin: [4, 8, 4, 8] });
  s.addText([
    { text: "Metrics", options: { bold: true, fontFace: "Georgia", fontSize: 16, color: C.text1, breakLine: true } },
    { text: "Accuracy (LLM judge + human corrections) · Recall@5 and Hit@5 against gold passages · failure-type counts · Cohen’s κ between annotators and vs. the judge", options: { fontSize: 13, color: C.text2 } },
  ], { x: 0.6, y: 4.65, w: 6.7, h: 1.4, margin: 0, valign: "top", paraSpaceAfter: 6, isTextBox: true });
  s.addChart(pres.charts.BAR, [{ name: "Questions", labels: ["Lookup", "Multi-hop", "Unanswerable", "Conflicting", "Ambiguous"], values: [40, 25, 19, 18, 11] }], {
    x: 7.7, y: 1.75, w: 5.0, h: 4.4, barDir: "bar", chartColors: [HEX.orange], showValue: true, dataLabelPosition: "outEnd",
    showLegend: false, showTitle: true, title: "Question set by type (n = 113)", titleFontSize: 14, titleColor: HEX.ink,
    catAxisOrientation: "maxMin", valAxisHidden: true, barGapWidthPct: 60, ...chartFrame, ...chartText, valGridLine: { style: "none" },
  });
  s.addNotes("BM25 is the classic baseline, dense retrieval is the standard RAG setup, the cross-encoder reranker is the newest method, and query rewriting is a second mitigation. All four use the same generator, prompt and k = 5. The 113 questions span five stress types. We started with 120 and dropped 7 bad ones during review.");
}

// ================================================================== 6 taxonomy
{
  const s = content("Method", "05 · THE TAXONOMY", "Six ways a RAG answer goes wrong");
  const tx = [
    ["R1", "Retrieval miss", "The needed passage is never retrieved."],
    ["R2", "Retrieved, ignored", "The passage comes back, but the model doesn’t use it."],
    ["R3", "Right chunk, wrong answer", "Misreads the passage, picks one reading of an ambiguous question, or gives outdated advice."],
    ["R4", "Hallucinated citation", "Cites a passage that doesn’t say that."],
    ["R5", "No-answer overreach", "Answers a question the docs can’t answer."],
    ["R6", "Multi-hop failure", "Answers one part of a two-part question, misses the other."],
  ];
  tx.forEach(([code, name, def], i) => {
    const col = i % 3, row = Math.floor(i / 3);
    const x = 0.6 + col * 4.1, y = 1.9 + row * 2.3;
    const n = totals(code);
    card(s, x, y, 3.8, 2.05, `${code} · ${name}`, def, { tSize: 13, hSize: 15 });
    s.addText([{ text: String(n), options: { bold: true, fontFace: "Georgia", fontSize: 20, color: n ? C.accent1 : C.accent6 } },
      { text: "  failures, all systems", options: { fontSize: 11, color: C.accent6 } }],
      { x: x + 0.25, y: y + 1.5, w: 3.3, h: 0.4, margin: 0, valign: "bottom", isTextBox: true });
  });
  s.addNotes("These are the six categories from our proposal. Each wrong answer gets exactly one primary cause, decided in order: unanswerable but answered is R5; info not retrieved is R1; retrieved but refused is R2; a bad citation is R4; one part of a two-part question missing is R6; otherwise the model misused a passage it had, which is R3. The counts are over all four systems, after human labeling.");
}

// ================================================================== 7 main results
pres.addSection({ title: "Results" });
{
  const s = content("Results", "06 · MAIN RESULTS", "Keyword search beat dense retrieval on both measures");
  s.addChart(pres.charts.BAR, [
    { name: "Accuracy", labels: SYS.map((x) => SYS_NAME[x]), values: SYS.map((x) => pct(S[x].accuracy)) },
    { name: "Recall@5", labels: SYS.map((x) => SYS_NAME[x]), values: SYS.map((x) => pct(S[x]["recall@5"])) },
  ], {
    x: 0.6, y: 1.75, w: 8.2, h: 4.9, barDir: "col", barGrouping: "clustered", chartColors: [HEX.ink, HEX.orange],
    showValue: true, dataLabelPosition: "outEnd", dataLabelFormatCode: '0.0"%"', valAxisMinVal: 0, valAxisMaxVal: 100,
    valAxisLabelFormatCode: '0"%"', showLegend: true, legendPos: "t", barGapWidthPct: 70, ...chartFrame, ...chartText,
  });
  const stats = [
    [`${pct(S.bm25.accuracy)}%`, "BM25 accuracy — best of all four"],
    [`+${(pct(S.dense_rerank["recall@5"]) - pct(S.dense["recall@5"])).toFixed(1)} pts`, "recall from the reranker…"],
    [`+${(pct(S.dense_rerank.accuracy) - pct(S.dense.accuracy)).toFixed(1)} pts`, "…but only this much accuracy"],
  ];
  stats.forEach(([n, l], i) => {
    const y = 1.95 + i * 1.55;
    s.addText(n, { x: 9.2, y, w: 3.5, h: 0.75, fontFace: "Georgia", fontSize: 36, bold: true, color: i ? C.accent1 : C.text1, margin: 0, isTextBox: true });
    s.addText(l, { x: 9.2, y: y + 0.75, w: 3.5, h: 0.5, fontSize: 14, color: C.text2, margin: 0, valign: "top", isTextBox: true });
  });
  s.addNotes(`BM25 had the highest accuracy, ${pct(S.bm25.accuracy)}%, and the highest recall, ${pct(S.bm25["recall@5"])}%. FastAPI docs are full of exact identifiers like response_model and OAuth2PasswordBearer, which keyword search matches well. Caveat: our questions were generated from chunk text, which favors lexical overlap. The reranker raised dense recall by about five points but accuracy by only about one, so better retrieval alone doesn’t fix most failures. Accuracy here is after human corrections; the raw LLM-judge numbers are on the judge slide.`);
}

// ================================================================== 8 failure distribution
{
  const s = content("Results", "07 · WHERE IT FAILS", "Most failures happen after retrieval succeeds");
  const cats = ["R1", "R2", "R3", "R6"];
  const catLab = { R1: "R1 Retrieval miss", R2: "R2 Retrieved, ignored", R3: "R3 Right chunk, wrong answer", R6: "R6 Multi-hop failure" };
  s.addChart(pres.charts.BAR, SYS.map((x) => ({ name: SYS_NAME[x], labels: cats.map((c) => catLab[c]), values: cats.map((c) => S[x][c]) })), {
    x: 0.6, y: 1.75, w: 8.4, h: 4.9, barDir: "col", barGrouping: "clustered", chartColors: SYS.map((x) => SYS_COLOR[x]),
    showValue: true, dataLabelPosition: "outEnd", showLegend: true, legendPos: "t", valAxisMinVal: 0, valAxisMajorUnit: 2,
    valAxisTitle: "Wrong answers", showValAxisTitle: true, valAxisTitleColor: HEX.muted, valAxisTitleFontSize: 11, valAxisTitleFontFace: "+mn-lt",
    barGapWidthPct: 50, ...chartFrame, ...chartText,
  });
  s.addText([
    { text: `${totals("R3")} of ${SYS.reduce((a, x) => a + S[x].failures, 0)}`, options: { fontFace: "Georgia", fontSize: 36, bold: true, color: C.accent1, breakLine: true } },
    { text: "failures are R3: the model had the right passage and still answered wrong. It is the top failure for every system.", options: { fontSize: 14, color: C.text2, breakLine: true } },
    { text: " ", options: { fontSize: 8, breakLine: true } },
    { text: "Retrieval misses (R1) are fewest for BM25. R4 and R5 never occurred.", options: { fontSize: 14, color: C.text2 } },
  ], { x: 9.4, y: 2.0, w: 3.3, h: 4.4, margin: 0, valign: "top", isTextBox: true });
  s.addNotes("This is our headline chart. For every system, the biggest bucket is R3: the right passage was retrieved, and the model still got it wrong, mostly by picking one reading of an ambiguous question or giving outdated advice. That’s why the reranker barely moved accuracy: it attacks R1, which is the smaller problem. We saw no hallucinated citations and no answers to unanswerable questions, which we discuss under limitations.");
}

// ================================================================== 9 heatmap
{
  const s = content("Results", "08 · FAILURES BY QUESTION TYPE", "Each question type breaks in its own way");
  const heat = { // dense baseline, final labels
    Lookup: [4, 0, 0, 0, 0, 0], "Multi-hop": [2, 1, 2, 0, 0, 6], Unanswerable: [0, 0, 0, 0, 0, 0],
    Ambiguous: [1, 0, 6, 0, 0, 0], Conflicting: [1, 1, 4, 0, 0, 0],
  };
  const shade = ["F1F3F6", "D6E4F7", "B3CDEF", "8BB3E6", "2A78D6", "1F5FAE", "0D3B7A"];
  const H = (t) => ({ text: t, options: { bold: true, color: C.text1, fill: { color: C.background2 }, align: "center" } });
  const rows = [[{ text: "Dense RAG", options: { bold: true, color: C.text2, fill: { color: C.background2 } } }, ...["R1", "R2", "R3", "R4", "R5", "R6"].map(H)]];
  for (const [t, vals] of Object.entries(heat)) {
    rows.push([{ text: t, options: { bold: true, color: C.text1, fill: { color: C.background2 } } },
      ...vals.map((v) => ({ text: v ? String(v) : "·", options: { align: "center", bold: v > 0, color: v >= 4 ? "FFFFFF" : (v ? HEX.ink : HEX.muted), fill: { color: shade[Math.min(v, 6)] } } }))]);
  }
  s.addTable(rows, { x: 0.6, y: 1.95, w: 7.6, colW: [1.9, 0.95, 0.95, 0.95, 0.95, 0.95, 0.95], fontSize: 16, rowH: 0.72, valign: "middle", border: { type: "solid", pt: 1.5, color: "F7F8FA" } });
  s.addText("Counts of wrong answers, Dense RAG (standard). Darker = more failures.", { x: 0.6, y: 6.4, w: 7.6, h: 0.35, fontSize: 11, color: C.accent6, margin: 0, isTextBox: true });
  const pts = [
    ["Lookup → R1", "Simple facts fail only when retrieval misses the page."],
    ["Multi-hop → R6", "The model answers one hop and drops the other."],
    ["Ambiguous & conflicting → R3", "It silently picks one reading, or the older advice."],
  ];
  pts.forEach(([h, t], i) => card(s, 8.6, 1.95 + i * 1.5, 4.1, 1.3, h, t, { hSize: 15, tSize: 13 }));
  s.addNotes("Breaking failures down by question type shows they cluster. Lookup questions only fail when retrieval misses. Multi-hop questions fail by answering one part. Ambiguous and conflicting questions fail by the model silently choosing one interpretation or the outdated approach. That suggests routing: different question types need different mitigations.");
}

// ================================================================== 10 accuracy by type
{
  const s = content("Results", "09 · ACCURACY BY QUESTION TYPE", "Query rewriting helps multi-hop; nothing fixes ambiguity");
  const types = [["acc_lookup", "Lookup"], ["acc_multi_hop", "Multi-hop"], ["acc_unanswerable", "Unanswerable"], ["acc_ambiguous", "Ambiguous"], ["acc_conflicting", "Conflicting"]];
  s.addChart(pres.charts.BAR, SYS.map((x) => ({ name: SYS_NAME[x], labels: types.map((t) => t[1]), values: types.map((t) => pct(S[x][t[0]])) })), {
    x: 0.6, y: 1.75, w: 8.6, h: 4.9, barDir: "col", barGrouping: "clustered", chartColors: SYS.map((x) => SYS_COLOR[x]),
    showValue: false, showLegend: true, legendPos: "t", valAxisMinVal: 0, valAxisMaxVal: 100, valAxisLabelFormatCode: '0"%"',
    barGapWidthPct: 50, ...chartFrame, ...chartText,
  });
  s.addText([
    { text: `${pct(S.dense.acc_multi_hop).toFixed(0)}% → ${pct(S.rewrite.acc_multi_hop).toFixed(0)}%`, options: { fontFace: "Georgia", fontSize: 32, bold: true, color: C.accent1, breakLine: true } },
    { text: "multi-hop accuracy, dense → query rewrite: the rewrite pulls in the second passage.", options: { fontSize: 14, color: C.text2, breakLine: true } },
    { text: " ", options: { fontSize: 10, breakLine: true } },
    { text: `≤ ${Math.round(Math.max(...SYS.map((x) => pct(S[x].acc_ambiguous))))}%`, options: { fontFace: "Georgia", fontSize: 32, bold: true, color: C.text1, breakLine: true } },
    { text: "ambiguous accuracy for every system: none of them asks which meaning you intended.", options: { fontSize: 14, color: C.text2 } },
  ], { x: 9.6, y: 2.0, w: 3.1, h: 4.5, margin: 0, valign: "top", isTextBox: true });
  s.addNotes("Lookup and unanswerable questions are nearly solved. Query rewriting gives the biggest gain on multi-hop questions, because the rewritten query brings in the second passage. Ambiguous questions stay below 50% for every system — no retrieval change fixes a model that never asks for clarification.");
}

// ================================================================== 11 judge reliability
{
  const s = pres.addSlide({ masterName: "DARK", sectionTitle: "Results" });
  s.addText("10 · CAN WE TRUST THE LLM JUDGE?", { placeholder: "eyebrow" });
  s.addText("Humans agree with each other, not with the LLM judge", { placeholder: "title" });
  const stats = [
    ["κ = 0.78", "Agreement between our two annotators (substantial)"],
    ["κ = 0.40", "Agreement between our final labels and the GPT-4o judge (fair)"],
    ["22", "Answers the judge marked wrong that both of us judged correct"],
  ];
  stats.forEach(([n, l], i) => {
    const x = 0.8 + i * 4.0;
    s.addText(n, { x, y: 2.75, w: 3.7, h: 0.95, fontFace: "Georgia", fontSize: 44, bold: true, color: C.accent1, margin: 0, isTextBox: true });
    s.addText(l, { x, y: 3.75, w: 3.5, h: 0.9, fontSize: 15, color: C.background2, margin: 0, valign: "top", isTextBox: true });
  });
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 0.8, y: 4.95, w: 11.7, h: 1.5, rectRadius: 0.08, fill: { color: "2A3445" }, line: { type: "none" }, objectName: "example panel" });
  s.addText([
    { text: "Example: ", options: { bold: true, color: C.accent1 } },
    { text: "the system answered with ", options: { color: C.background2 } },
    { text: "router.frontend()", options: { fontFace: "Consolas", color: C.background1 } },
    { text: ", a new FastAPI feature documented in the corpus. The judge marked all four answers wrong; its built-in knowledge was older than the docs.", options: { color: C.background2, breakLine: true } },
    { text: `After human corrections, dense accuracy is ${pct(S.dense.accuracy)}%, versus 66.7% from the judge alone. We also dropped 4 questions with broken gold answers.`, options: { color: C.accent6, fontSize: 14 } },
  ], { x: 1.1, y: 5.1, w: 11.1, h: 1.5, fontSize: 16, margin: 0, valign: "top", paraSpaceAfter: 6, isTextBox: true });
  s.addNotes("We both labeled all 140 failures independently. Our agreement was κ = 0.78, which is substantial. Agreement with the GPT-4o judge was only 0.40. Most disagreements came from the judge being too strict or out of date: for example, it marked router.frontend() answers wrong because the API is newer than its training data, even though it’s in the docs we indexed. We corrected 22 such judge errors and dropped 4 questions whose gold answers were wrong. Lesson: an LLM judge alone can’t explain RAG failures.");
}

// ================================================================== 12 takeaways
pres.addSection({ title: "Conclusion" });
{
  const s = content("Conclusion", "11 · TAKEAWAYS", "What we learned about where RAG breaks");
  const items = [
    ["Keyword retrieval wins on technical docs", `BM25 reached ${pct(S.bm25.accuracy)}% accuracy vs. ${pct(S.dense.accuracy)}% for dense; exact API names favor lexical matching.`],
    ["Better retrieval doesn’t fix most failures", "The reranker added ~5 pts recall and ~1 pt accuracy. The dominant failure, R3, happens after retrieval."],
    ["Failures cluster by question type", "Lookup → R1, multi-hop → R6, ambiguous/conflicting → R3. Mitigations should be routed by type."],
    ["Don’t trust an LLM judge alone", "κ = 0.40 against human labels; it penalized correct answers about newer APIs."],
  ];
  items.forEach(([h, t], i) => {
    const y = 1.9 + i * 1.2;
    s.addShape(pres.shapes.OVAL, { x: 0.6, y: y + 0.05, w: 0.6, h: 0.6, fill: { color: i === 1 ? C.accent1 : C.text1 }, line: { type: "none" }, objectName: `takeaway ${i + 1} badge` });
    s.addText(String(i + 1), { x: 0.6, y: y + 0.05, w: 0.6, h: 0.6, fontFace: "Georgia", fontSize: 18, bold: true, color: C.background1, align: "center", valign: "middle", margin: 0, isTextBox: true });
    s.addText([
      { text: h, options: { fontFace: "Georgia", fontSize: 18, bold: true, color: C.text1, breakLine: true } },
      { text: t, options: { fontSize: 14, color: C.text2 } },
    ], { x: 1.5, y, w: 11.2, h: 1.0, margin: 0, valign: "top", paraSpaceAfter: 3, isTextBox: true });
  });
  s.addNotes("Four takeaways. One: on technical documentation, keyword search beat dense embeddings. Two: improving retrieval helps less than you’d think, because most failures happen after retrieval. Three: failures cluster by question type, so a single mitigation won’t fix everything. Four: LLM judges need human validation.");
}

// ================================================================== 13 limitations
{
  const s = content("Conclusion", "12 · LIMITATIONS & NEXT STEPS", "What would make these results stronger");
  card(s, 0.6, 1.9, 5.9, 3.7, "Limitations", "", { hSize: 18 });
  s.addText([
    "Questions were LLM-generated from chunk text, which can favor BM25",
    "One corpus, one generator model, k = 5",
    "113 questions: gaps of a few points need significance testing",
    "Zero R5: the unanswerable questions were too easy",
    "R4 may be under-counted; citations weren’t verified line by line",
  ].map((t, i, a) => ({ text: t, options: { bullet: true, breakLine: i < a.length - 1 } })),
  { x: 0.85, y: 2.55, w: 5.4, h: 3.8, fontSize: 14, color: C.text2, paraSpaceAfter: 8, margin: 0, valign: "top", isTextBox: true });
  card(s, 6.8, 1.9, 5.9, 3.7, "Next steps", "", { hSize: 18, hColor: C.accent1 });
  s.addText([
    "Bootstrap confidence intervals and McNemar tests between systems",
    "Ablations: k = 3/5/10 and a stronger generator (GPT-4o)",
    "Harder unanswerable questions that share keywords with real pages",
    "Automatic citation checking to measure R4",
    "Route mitigations by question type: rewrite for multi-hop, clarify for ambiguous",
  ].map((t, i, a) => ({ text: t, options: { bullet: true, breakLine: i < a.length - 1 } })),
  { x: 7.05, y: 2.55, w: 5.4, h: 3.8, fontSize: 14, color: C.text2, paraSpaceAfter: 8, margin: 0, valign: "top", isTextBox: true });
  s.addNotes("Main limitations: the questions were generated from the docs, which likely helps BM25; one corpus and one generator; and with 113 questions, small gaps may not be significant. We saw zero R5, so our unanswerable questions were too easy, and R4 may be under-counted. Next we’ll add significance tests, ablations, harder unanswerables and citation checking.");
}

// ================================================================== 14 end
{
  const s = pres.addSlide({ masterName: "DARK_TITLE", sectionTitle: "Conclusion" });
  s.addText("Thank you", { placeholder: "title" });
  s.addText([
    { text: "Code: ", options: { bold: true, color: C.accent1 } },
    { text: "[GitHub link]", options: { color: C.background2, breakLine: true } },
    { text: "dhc0018@auburn.edu · hyn0001@auburn.edu", options: { color: C.accent6 } },
  ], { x: 0.8, y: 4.0, w: 9, h: 1.0, fontSize: 16, margin: 0, valign: "top", paraSpaceAfter: 6, isTextBox: true });
  s.addNotes("Thanks. Happy to take questions.");
}

(async () => {
  await pres.writeFile({ fileName: OUT });
  await applyTheme(OUT, THEME);
  console.log("wrote", OUT);
})();
