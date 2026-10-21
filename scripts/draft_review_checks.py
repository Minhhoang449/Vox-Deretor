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


def studio_checks(paragraphs, text):
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
    est = round(elapsed, 1)
    if est and not 8 <= est <= 16:
        out.append({"kind": "runtime_out_of_range", "minutes_estimate": est,
                    "action": "Target 8-16 min set by the evidence; do not pad."})
    return out, est


def review(text, evidence=None):
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
    studio, est_minutes = studio_checks(paragraphs, text)
    findings.extend(studio)
    studio = studio_rules(paragraphs) if paragraphs else None
    return {
        "status": "diagnostics_only",
        "studio_rules": studio,
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
        "limits": "Exact repeats, Studio heuristics (early hedges, hedge density, one-sentence paragraphs, repeated figures/names, token-overlap repeats, runtime estimate) and mapping structure. No semantic model, source verification, timing, full claim coverage, performance forecast or approval. Zero findings does not pass a draft.",
    }


# --- Studio rules (user-approved 21-22/10/2026) -----------------------------
import re as _re

RATES = {"en": ("words", 150), "vi": ("words", 160), "ja": ("chars", 300)}
HEDGES = {
    "en": [r"\bmay\b", r"\bmight\b", r"\bperhaps\b", r"\bprobably\b", r"\bpossibly\b",
           r"\blikely\b", r"\bunclear\b", r"\buncertain\b", r"\bwe don'?t know\b",
           r"\bnot certain\b", r"\bseems?\b", r"\bappears? to\b", r"\bcannot be sure\b",
           r"\bdebated?\b", r"\bnot (?:necessarily|always)\b"],
    "vi": [r"có lẽ", r"có thể", r"chưa chắc", r"không rõ", r"giả thuyết", r"dường như",
           r"được cho là", r"chưa thể khẳng định"],
    "ja": [r"かもしれ", r"考えられ", r"とみられ", r"可能性", r"推定", r"はっきりし",
           r"わかっていな", r"分かっていな", r"断定", r"とは限ら", r"らしい"],
}


def detect_language(text):
    cjk = len(_re.findall(r"[\u3040-\u30ff\u4e00-\u9fff]", text))
    if cjk > len(text) * 0.2:
        return "ja"
    if _re.search(r"[ăâđêôơưạảấầẩẫậắằẳẵặẹẻẽếềểễệỉịọỏốồổỗộớờởỡợụủứừửữựỳỵỷỹ]", text.lower()):
        return "vi"
    return "en"


def _sentences(paragraph, lang):
    pattern = r"(?<=[。！？!?])" if lang == "ja" else r"(?<=[.!?])\s+"
    return [s.strip() for s in _re.split(pattern, paragraph) if s.strip()]


def _units(text, lang):
    return len(_re.sub(r"\s", "", text)) if lang == "ja" else len(text.split())


def _grams(sentence, lang):
    if lang == "ja":
        s = _re.sub(r"[\s、。！？「」]", "", sentence)
        return {s[i:i + 3] for i in range(max(len(s) - 2, 0))}
    w = _re.findall(r"\w+", sentence.casefold())
    return {" ".join(w[i:i + 2]) for i in range(max(len(w) - 1, 0))}


def studio_rules(paragraphs, lang=None):
    """Hard Studio gates. Any finding with blocking=True blocks presenting the draft."""
    full = "\n\n".join(p for _, p in paragraphs)
    lang = lang or detect_language(full)
    unit, rate = RATES[lang]
    found, elapsed, hedge_sentences = [], 0.0, []
    sents = []
    for line, para in paragraphs:
        ss = _sentences(para, lang)
        if len(ss) == 1 and len(paragraphs) > 1:
            found.append({"rule": "no_single_sentence_paragraph", "line": line,
                          "blocking": True, "excerpt": para,
                          "action": "Merge into the neighbouring paragraph."})
        for s in ss:
            t = elapsed / rate
            sents.append((line, t, s))
            if any(_re.search(h, s, _re.I) for h in HEDGES[lang]):
                hedge_sentences.append((line, t, s))
            elapsed += _units(s, lang)
    early = [h for h in hedge_sentences if h[1] < 2.0]
    for line, t, s in early:
        found.append({"rule": "no_caveat_before_2min", "line": line, "minute": round(t, 2),
                      "blocking": True, "excerpt": s,
                      "action": "Move after 2:00 or drop; the opening states what is known."})
    if len(hedge_sentences) > 4:
        found.append({"rule": "max_4_caveat_sentences", "blocking": True,
                      "count": len(hedge_sentences),
                      "lines": [h[0] for h in hedge_sentences],
                      "action": "Keep the 3-4 caveats that change the answer; say each once."})
    first_min = [s for s in sents if s[1] < 1.0]
    if not any(_re.search(r"[?？]|か。$|のか", s[2]) for s in first_min):
        found.append({"rule": "question_within_60s", "blocking": True,
                      "action": "State the main question and the hanging question in the first minute."})
    nums = {}
    for line, para in paragraphs:
        for n in set(_re.findall(r"\d[\d.,]*", para)):
            nums.setdefault(n, []).append(line)
    for n, where in nums.items():
        if len(where) > 2:
            found.append({"rule": "idea_max_twice", "token": n, "lines": where,
                          "blocking": True,
                          "action": "Number repeated in >2 paragraphs; keep first use and payoff only."})
    for i in range(len(sents)):
        gi = _grams(sents[i][2], lang)
        for j in range(i + 2, len(sents)):
            gj = _grams(sents[j][2], lang)
            if len(gi) > 3 and len(gj) > 3 and len(gi & gj) / len(gi | gj) >= 0.4:
                found.append({"rule": "idea_max_twice", "kind": "paraphrase",
                              "lines": [sents[i][0], sents[j][0]], "blocking": False,
                              "excerpt": [sents[i][2], sents[j][2]],
                              "action": "Likely restatement; check whether the second adds anything."})
    if len(paragraphs) > 2:
        g1, g2 = _grams(paragraphs[0][1], lang), _grams(paragraphs[-1][1], lang)
        if not g1 & g2:
            found.append({"rule": "close_loop_to_opening", "blocking": True,
                          "action": "Ending should return to the opening object/scene with its changed meaning."})
    return {"language": lang, "estimated_minutes": round(elapsed / rate, 1),
            "caveat_sentences": len(hedge_sentences),
            "blocking": sum(1 for f in found if f.get("blocking")),
            "findings": found}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("narration", type=Path)
    parser.add_argument("--evidence", type=Path,
                        help="Optional JSON list: line, quote, source_locator, support")
    args = parser.parse_args()
    text = args.narration.read_text(encoding="utf-8-sig")
    evidence = (json.loads(args.evidence.read_text(encoding="utf-8-sig"))
                if args.evidence else None)
    try:
        result = review(text, evidence)
    except ValueError as error:
        parser.error(str(error))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
