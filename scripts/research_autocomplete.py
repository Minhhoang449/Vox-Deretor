#!/usr/bin/env python3
"""YouTube autocomplete check and title gate (Studio SEO rule).

Autocomplete shows that people type a phrase; it never gives search volume.
Labels per phrase:
  searched      - a suggestion contains every token of the phrase
  check_intent  - suggestions exist but none contain the whole phrase
                  (e.g. "amarna" -> "amarnath"); a human must confirm intent
  no_suggestions- nothing returned; use only in description/tags
  fetch_error   - network failure; recorded, never treated as evidence

Title gate (hard): a `searched` phrase must start within the head window
(40 chars en/vi, 20 chars ja) and the title must fit the length cap
(60 chars en/vi, 32 chars ja).

Usage:
  python scripts/research_autocomplete.py --channel chikyu-shikumi \
      --title "..." --phrase "栃の実 食べ方" --phrase "唐堀遺跡" [--json out.json]
"""
import argparse, json, re, sys, time, unicodedata, urllib.parse, urllib.request
from pathlib import Path

MARKET = {"ja": ("ja", "JP"), "vi": ("vi", "VN"), "en": ("en", "US")}
HEAD = {"ja": 20}
CAP = {"ja": 32}
ENDPOINT = "https://suggestqueries.google.com/complete/search"


def fold(text):
    return unicodedata.normalize("NFKC", text).casefold().replace("’", "'")


def tokens(text):
    return [t for t in re.split(r"[\s　・、,?？!！:：|｜]+", fold(text)) if t]


def channel_language(slug):
    cfg = json.loads((Path(__file__).resolve().parents[1] / "config/channels.json").read_text("utf-8"))
    channels = cfg.get("channels", cfg)
    if isinstance(channels, dict) and isinstance(channels.get(slug), dict):
        return channels[slug].get("language", "en")
    for value in channels if isinstance(channels, list) else []:
        if value.get("id") == slug:
            return value.get("language", "en")
    raise SystemExit(f"unknown channel: {slug}")


def fetch(phrase, hl, gl, opener=None):
    query = urllib.parse.urlencode({"client": "firefox", "ds": "yt", "hl": hl, "gl": gl, "q": phrase})
    opener = opener or urllib.request.urlopen
    with opener(f"{ENDPOINT}?{query}", timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))[1]


def label(phrase, suggestions):
    if not suggestions:
        return "no_suggestions"
    need = tokens(phrase)
    for s in suggestions:
        have = fold(s)
        words = set(tokens(s))
        # Spaced languages: whole-word match ("hồ" must not match "hồng").
        if all((t in words) if " " in have else (t in have) for t in need):
            return "searched"
    return "check_intent"


def check_phrases(phrases, language, fetcher=fetch):
    hl, gl = MARKET.get(language, ("en", "US"))
    rows = []
    for phrase in phrases:
        try:
            sugg = fetcher(phrase, hl, gl)
            rows.append({"phrase": phrase, "label": label(phrase, sugg), "suggestions": sugg})
        except Exception as exc:  # network blocked: record, never guess
            rows.append({"phrase": phrase, "label": "fetch_error", "suggestions": [], "error": str(exc)})
        time.sleep(0.2)
    return rows


def title_gate(title, rows, language):
    head, cap = HEAD.get(language, 40), CAP.get(language, 60)
    problems = []
    if len(title) > cap:
        problems.append(f"title is {len(title)} chars; cap is {cap}")
    folded = fold(title)
    hits = []
    for row in rows:
        if row["label"] != "searched":
            continue
        first = tokens(row["phrase"])[0]
        pos = folded.find(first)
        if pos != -1 and all(t in folded for t in tokens(row["phrase"])):
            hits.append((row["phrase"], pos))
    if not hits:
        problems.append("no phrase labelled `searched` appears in the title")
    elif min(p for _, p in hits) > head:
        problems.append(f"first searched phrase starts at char {min(p for _, p in hits)}; must start within {head}")
    if any(r["label"] == "fetch_error" for r in rows):
        problems.append("some phrases could not be fetched; gate result is incomplete")
    return {"title": title, "length": len(title), "cap": cap, "head_window": head,
            "searched_in_title": [h[0] for h in hits], "pass": not problems, "problems": problems}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--channel", required=True)
    ap.add_argument("--title", required=True)
    ap.add_argument("--phrase", action="append", required=True)
    ap.add_argument("--json")
    a = ap.parse_args(argv)
    lang = channel_language(a.channel)
    rows = check_phrases(a.phrase, lang)
    gate = title_gate(a.title, rows, lang)
    report = {"channel": a.channel, "language": lang, "phrases": rows, "gate": gate,
              "note": "Autocomplete proves typing, not volume. Volume: YouTube Studio Research tab."}
    text = json.dumps(report, ensure_ascii=False, indent=2)
    if a.json:
        Path(a.json).write_text(text, "utf-8")
    print(text)
    return 0 if gate["pass"] else 2


if __name__ == "__main__":
    sys.exit(main())
