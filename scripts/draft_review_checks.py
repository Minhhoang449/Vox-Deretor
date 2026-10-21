"""Local draft diagnostics; never factual verification or narration approval."""
import argparse
import hashlib
import json
from pathlib import Path


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
    return {
        "status": "diagnostics_only",
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
        "limits": "Exact repeats and mapping structure only. No semantic model, source verification, timing, full claim coverage, performance forecast or approval. Zero findings does not pass a draft.",
    }


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
