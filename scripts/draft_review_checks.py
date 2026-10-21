"""Local draft diagnostics; never factual verification or narration approval."""
import argparse
import hashlib
import json
from pathlib import Path

import re
from collections import Counter

HEDGES = ["may ", "might ", "likely", "perhaps", "probably", "suggests", "we can't know",
          "we cannot know", "not a claim", "it is unclear", "uncertain",
          "かもしれ", "考えられ", "とは限らない", "わかりません", "わかっていない", "可能性",
          "có lẽ", "có thể", "chưa chắc", "không rõ"]
WORDS_PER_MIN = {"latin": 150, "cjk": 300}


def _sentences(paragraph):
    return [x for x in re.split(r"(?<=[.!?。！？])\s*", paragraph) if x.strip()]


def _is_cjk(text):
    return sum(1 for c in text if "\u3040" <= c <= "\u9fff") > len(text) * 0.2


def _tokens(text):
    if _is_cjk(text):
        t = re.sub(r"\s", "", text)
        return {t[i:i + 2] for i in range(len(t) - 1)}
    return {w for w in re.findall(r"[\w']+", text.casefold()) if len(w) > 3}


VAGUE_TIME = re.compile(r"\b(?:one|that) (?:autumn|spring|summer|winter|morning|evening|year)\b|\bone day\b", re.I)


def studio_checks(paragraphs, text, target_minutes=None):
    """Studio Rules v1.0 heuristics (user-approved 2026-10-21). Flags, not verdicts."""
    out = []
    cjk = _is_cjk(text)
    rate = WORDS_PER_MIN["cjk" if cjk else "latin"]
    elapsed = 0.0
    for line, para in paragraphs:
        size = len(re.sub(r"\s", "", para)) if cjk else len(para.split())
        low = para.casefold()
        if elapsed < 2.0:
            for h in HEDGES:
                if h in low:
                    out.append({"kind": "early_hedge", "line": line, "term": h.strip(),
                                "minute": round(elapsed, 2),
                                "action": "No hedge before 2:00 unless the hook itself is uncertain."})
                    break
        elapsed += size / rate
        if len(_sentences(para)) == 1 and size > 0:
            out.append({"kind": "one_sentence_paragraph", "line": line, "excerpt": para[:80],
                        "action": "Merge into the neighbouring paragraph."})
    hedge_total = sum(p.casefold().count(h) for _, p in paragraphs for h in HEDGES)
    if hedge_total > 4:
        out.append({"kind": "hedge_density", "count": hedge_total,
                    "action": "State each uncertainty once, at its claim; cut repeats (target <=4)."})
    # numbers and proper names repeated more than twice
    nums = Counter(re.findall(r"\d[\d,.]*\s?(?:km|m|kg|l|litres?|liters?|years?|メートル|年|キロ)?", text))
    for n, c in nums.items():
        if c > 2 and len(n.strip()) > 1:
            out.append({"kind": "repeated_number", "value": n.strip(), "count": c,
                        "action": "Mention a figure at most twice."})
    if not cjk:
        names = Counter(m for m in re.findall(r"(?<![.!?]\s)(?<!^)\b[A-Z][a-z]{3,}\b", text))
        for n, c in names.items():
            if c > 4:
                out.append({"kind": "repeated_name", "value": n, "count": c,
                            "action": "Check each mention adds something; use pronouns."})
    # semantic near-repeat across paragraphs (Jaccard on content tokens)
    toks = [(l, _tokens(p), p) for l, p in paragraphs]
    for i in range(len(toks)):
        for j in range(i + 1, len(toks)):
            a, b = toks[i][1], toks[j][1]
            if len(a) < 6 or len(b) < 6:
                continue
            sim = len(a & b) / len(a | b)
            if sim >= 0.35:
                out.append({"kind": "semantic_repeat", "line": toks[j][0],
                            "related_line": toks[i][0], "similarity": round(sim, 2),
                            "action": "Same idea explained again? Keep one, cut or merge the other."})
    # vague dating with no source date
    for line, para in paragraphs:
        m = VAGUE_TIME.search(para)
        if m:
            out.append({"kind": "vague_time", "line": line, "term": m.group(0),
                        "action": "Use the dated wording from the source (e.g. the ancient calendar date) or cut it."})
        n = len(re.findall(r"\b\d[\d,.]*\b", para))
        if n > 3:
            out.append({"kind": "number_dense_paragraph", "line": line, "count": n,
                        "action": "Keep at most 3 figures per paragraph; put the rest on screen."})
    # hanging question must be re-raised around 1/3 and 2/3 of the runtime
    if paragraphs and not cjk:
        sizes = [len(p.split()) for _, p in paragraphs]
        total = sum(sizes) or 1
        pos, q = 0, None
        for (line, para), sz in zip(paragraphs, sizes):
            if pos / total * elapsed <= 1.0 and "?" in para:
                q = set().union(*(_tokens(x) for x in _sentences(para) if "?" in x))
            pos += sz
        if q and len(q) >= 2:
            pos = 0
            hits = set()
            for (line, para), sz in zip(paragraphs, sizes):
                frac = pos / total
                if 0.2 <= frac <= 0.8 and len(q & _tokens(para)) >= 2:
                    hits.add("first" if frac < 0.5 else "second")
                pos += sz
            for half in ("first", "second"):
                if half not in hits:
                    out.append({"kind": "missing_mid_rehook", "half": half,
                                "action": "Re-raise the opening question in one line around "
                                          + ("1/3" if half == "first" else "2/3") + " of the runtime."})
    est = round(elapsed, 1)
    if est and target_minutes and est < target_minutes * 0.85:
        out.append({"kind": "runtime_below_target", "minutes_estimate": est, "target": target_minutes,
                    "action": "Below the channel's competitor-based target; add sourced material, no padding."})
    if est and not 8 <= est <= 16:
        out.append({"kind": "runtime_out_of_range", "minutes_estimate": est,
                    "action": "Target 8-16 min set by the evidence; do not pad."})
    return out, est


NARRATION_HEADINGS = ("## lời dẫn", "## narration", "## ナレーション")


def narration_only(text):
    """If the file has a narration heading, keep only that section (notes and source tables excluded)."""
    out, keep, found = [], False, False
    for line in text.splitlines():
        low = line.strip().casefold()
        if low.startswith("#"):
            if low in NARRATION_HEADINGS:
                keep, found = True, True
                out.append("")
                continue
            if keep and low.startswith("## "):
                keep = False
        out.append(line if keep else "")
    return "\n".join(out) if found else text


def review(text, evidence=None, target_minutes=None):
    raw = text
    text = narration_only(text)
    lines = text.splitlines()
    paragraphs = []
    start, chunk = 1, []
    for number, line in enumerate(lines + [""], 1):
        if line.strip():
            if not chunk:
                start = number
            chunk.append(line.strip())
        elif chunk:
            paragraphs.append((start, " ".join(chunk)))
            chunk = []
    findings, seen = [], {}
    for line, paragraph in paragraphs:
        normalized = " ".join(paragraph.split()).casefold()
        if normalized in seen:
            findings.append({"kind": "exact_paragraph_repeat", "line": line,
                             "related_line": seen[normalized],
                             "excerpt": paragraph,
                             "action": "Inspect contribution; merge or cut if no distinct purpose."})
        else:
            seen[normalized] = line
    claims = []
    if evidence is not None:
        if not isinstance(evidence, list):
            raise ValueError("Evidence must be a list of claim records.")
        for index, item in enumerate(evidence, 1):
            if not isinstance(item, dict):
                raise ValueError("Each claim record must be an object.")
            quote = item.get("quote", "")
            locator = item.get("source_locator", "")
            rationale = item.get("support", "")
            line = item.get("line")
            if (isinstance(line, bool) or not isinstance(line, int)
                    or not 1 <= line <= len(lines)):
                problem = "Provide a valid one-based narration line."
            elif not isinstance(quote, str) or not quote or quote not in lines[line - 1]:
                problem = "Claim quote does not match the specified current narration line."
            elif not isinstance(locator, str) or not locator.strip():
                problem = "Source locator missing."
            elif not isinstance(rationale, str) or not rationale.strip():
                problem = "Explain how the inspected source supports this exact wording."
            else:
                problem = None
            claims.append({"record": index, "line": line,
                           "status": "needs_fix" if problem else "mapped_not_verified"})
            if problem:
                findings.append({"kind": "evidence_mapping", "record": index,
                                 "line": line, "action": problem})
    studio, est_minutes = studio_checks(paragraphs, text, target_minutes)
    findings.extend(studio)
    for i, l in enumerate(raw.splitlines(), 1):
        if re.search(r"NEEDS[ _]SOURCE|\bTODO\b|\[source\?\]", l, re.I):
            findings.append({"kind": "unsourced_marker", "line": i, "excerpt": l.strip()[:80],
                             "action": "Source the claim or cut it before review; no open markers."})
    return {
        "status": "diagnostics_only",
        "estimated_minutes": est_minutes,
        "speech_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "fingerprint_method": "UTF-8 text as read; separate from the approval fingerprint",
        "paragraph_count": len(paragraphs),
        "findings": findings,
        "claim_mappings": claims,
        "evidence_coverage": "not_established",
        "manual_checks_required": [
            "Semantic repetition and each passage's distinct contribution",
            "Hook truth, analogy limits and answer actually delivered",
            "All historical scene roles, numbers and science against inspected sources",
            "Changed scene details and claim strength against prior version and sources",
            "Material uncertainty remains attached to affected claims",
            "Actual title/thumbnail/opening/middle/ending alignment and native voice",
        ],
        "limits": "Exact repeats, Studio heuristics (early hedges, hedge density, one-sentence paragraphs, repeated figures/names, token-overlap repeats, vague dates, number-dense paragraphs, mid-video re-hooks, open source markers, runtime vs target) and mapping structure. No semantic model, source verification, timing, full claim coverage, performance forecast or approval. Zero findings does not pass a draft.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("narration", type=Path)
    parser.add_argument("--evidence", type=Path,
                        help="Optional JSON list: line, quote, source_locator, support")
    parser.add_argument("--target-minutes", type=float,
                        help="Channel target from research_packaging target_length (minutes)")
    parser.add_argument("--packaging", type=Path,
                        help="research_packaging JSON; reads youtube_metadata.target_length.target_minutes")
    args = parser.parse_args()
    if args.packaging and args.target_minutes is None:
        pk = json.loads(args.packaging.read_text(encoding="utf-8-sig"))
        args.target_minutes = (pk.get("youtube_metadata", {}).get("target_length", {})
                               .get("target_minutes"))
    text = args.narration.read_text(encoding="utf-8-sig")
    evidence = (json.loads(args.evidence.read_text(encoding="utf-8-sig"))
                if args.evidence else None)
    try:
        result = review(text, evidence, args.target_minutes)
    except ValueError as error:
        parser.error(str(error))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
