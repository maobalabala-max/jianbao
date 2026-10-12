#!/usr/bin/env python3
"""Validate a combined-briefing data file (JSON) against EDITORIAL_SPEC hard limits.

usage: python3 tools/validate_briefing.py /workspace/daily-briefing/data/YYYY-MM-DD.json [--html OUT.html]
Exit 0 = pass (warnings may print), 1 = errors (each printed as ERROR ...). Fails loudly by design.
"""
from __future__ import annotations

import json
import re
import sys
from datetime import date
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from briefing_common import (  # noqa: E402
    ALL_TAGS, BANNED_HOSTS, EVIDENCE_TAGS, JARGON, PROCESS_NOTES, SECTION_LIMITS, SECTIONS, SITE,
    SUBJECT_TAGS, URL_RE, blocked_patterns, han, strip_tags, zlen,
)

LIM = dict(summary=90, top_lead=16, top_fact=70, top_an=40, title=28, lede=80, detail=120, why=60,
           watch=40, prev=40, story_total=280, brief_title=20, brief_text=60, briefs_per_sec=5,
           body_han=3500, stories_max=12, stories_min=9)
SEC_KEYS = [k for k, _, _ in SECTIONS]


def load(path: str | Path) -> dict:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    assign_ids(data)
    return data


def assign_ids(data: dict) -> None:
    n = 0
    for k in SEC_KEYS:
        sec = data.get("sections", {}).get(k) or {}
        for st in sec.get("stories", []) or []:
            n += 1
            st.setdefault("id", f"i{n}")
        for j, b in enumerate(sec.get("briefs", []) or [], 1):
            b.setdefault("id", f"b-{k}-{j}")


def story_text(st: dict) -> list[str]:
    return [st.get(f) or "" for f in ("title", "lede", "detail", "why", "watch", "prev")]


def all_text(data: dict) -> list[tuple[str, str]]:
    """(where, text) for every reader-visible prose field (not URLs)."""
    out = [("summary", data.get("summary") or ""), ("notes", data.get("notes") or "")]
    for i, t in enumerate(data.get("top3") or [], 1):
        for f in ("lead", "fact", "analysis"):
            out.append((f"top3[{i}].{f}", t.get(f) or ""))
    for k in SEC_KEYS:
        sec = data.get("sections", {}).get(k) or {}
        for f in ("empty", "skipped"):
            out.append((f"{k}.{f}", sec.get(f) or ""))
        for st in sec.get("stories", []) or []:
            for f in ("org", "title", "lede", "detail", "why", "watch", "prev"):
                out.append((f"{st.get('id')}.{f}", st.get(f) or ""))
            for s in st.get("sources", []) or []:
                out.append((f"{st.get('id')}.source.name", s.get("name") or ""))
        for b in sec.get("briefs", []) or []:
            for f in ("title", "text"):
                out.append((f"{b.get('id')}.{f}", b.get(f) or ""))
            for s in b.get("sources", []) or []:
                out.append((f"{b.get('id')}.source.name", s.get("name") or ""))
    for i, c in enumerate(data.get("corrections") or [], 1):
        out.append((f"corrections[{i}].text", c.get("text") or ""))
    return out


def check_tags(where: str, tags, sec: str, errs: list, is_story: bool) -> None:
    if not isinstance(tags, list) or not tags:
        errs.append(f"{where}: tags missing")
        return
    bad = [t for t in tags if t not in ALL_TAGS]
    if bad:
        errs.append(f"{where}: unknown tag(s) {bad}; allowed: {sorted(ALL_TAGS)}")
    ev = [t for t in tags if t in EVIDENCE_TAGS]
    if not 1 <= len(ev) <= 2:
        errs.append(f"{where}: needs 1–2 evidence tags from {sorted(EVIDENCE_TAGS)}, got {ev}")
    if "rumor" in ev and any(t in ev for t in ("off", "peer", "cross")):
        errs.append(f"{where}: contradictory tags {ev} (rumor cannot be combined with off/peer/cross)")
    if sec == "lon" and not any(t in SUBJECT_TAGS for t in tags):
        errs.append(f"{where}: 抗衰 items must carry a subject tag from {sorted(SUBJECT_TAGS)}")


def check_sources(where: str, srcs, errs: list) -> None:
    if not isinstance(srcs, list) or not srcs:
        errs.append(f"{where}: at least one source required")
        return
    for s in srcs:
        name, url = (s or {}).get("name", ""), (s or {}).get("url", "")
        if not name or URL_RE.search(name):
            errs.append(f"{where}: source name must be an institution name, not empty/URL: {name!r}")
        if not re.match(r"https?://[^\s]+$", url or ""):
            errs.append(f"{where}: bad source url {url!r}")
        if any(h in (url or "") for h in BANNED_HOSTS):
            errs.append(f"{where}: {url} is a syndication mirror; link the original publisher")


def lim(errs, where, text, key, label=None):
    n = zlen(text or "")
    if n > LIM[key]:
        errs.append(f"{where}: {label or key} {n:g} 字 > {LIM[key]} — {strip_tags(text)[:40]}…")


def validate(data: dict, path: Path | None = None, html_path: Path | None = None) -> tuple[list, list]:
    errs: list[str] = []
    warns: list[str] = []
    d = data.get("date", "")
    try:
        date.fromisoformat(d)
    except Exception:
        errs.append(f"date: invalid {d!r}")
    if path and path.stem != d:
        warns.append(f"file name {path.name} does not match date {d}")
    if not data.get("summary"):
        errs.append("summary: required (one-line thesis; becomes <p class=\"lede\"> / meta description)")
    lim(errs, "summary", data.get("summary"), "summary")

    ids, id_sec = set(), {}
    total = 0
    for k in SEC_KEYS:
        sec = (data.get("sections") or {}).get(k)
        if sec is None:
            errs.append(f"sections.{k}: missing (use \"empty\": \"今日从缺…\" if nothing qualifies)")
            continue
        stories, briefs = sec.get("stories") or [], sec.get("briefs") or []
        lo, hi = SECTION_LIMITS[k]
        if not lo <= len(stories) <= hi:
            errs.append(f"sections.{k}: {len(stories)} 条要闻, limit {lo}–{hi}")
        if len(briefs) > LIM["briefs_per_sec"]:
            errs.append(f"sections.{k}: {len(briefs)} 条简讯 > {LIM['briefs_per_sec']}")
        if not stories and not briefs and not sec.get("empty"):
            errs.append(f"sections.{k}: empty section needs an \"empty\" note (今日从缺)")
        total += len(stories)
        for st in stories:
            w = st.get("id", "?")
            if w in ids:
                errs.append(f"{w}: duplicate id")
            ids.add(w)
            id_sec[w] = k
            for f in ("title", "lede", "why", "org"):
                if not (st.get(f) or "").strip():
                    errs.append(f"{w}: field '{f}' required")
            if "watch" not in st:
                errs.append(f"{w}: field 'watch' required (string, or null when there is no checkable next step)")
            for f in ("title", "lede", "detail", "why", "watch", "prev"):
                lim(errs, w, st.get(f), f)
            tot = sum(zlen(x) for x in story_text(st)[1:])
            if tot > LIM["story_total"]:
                errs.append(f"{w}: story body {tot:g} 字 > {LIM['story_total']}")
            if "why_analysis" in st and not isinstance(st["why_analysis"], bool):
                errs.append(f"{w}: why_analysis must be true/false")
            check_tags(w, st.get("tags"), k, errs, True)
            check_sources(w, st.get("sources"), errs)
            tags = st.get("tags") or []
            if (len(st.get("sources") or []) == 1 and k in ("ai", "tech")
                    and any(t in tags for t in ("media", "paywall", "rumor")) and "single" not in tags):
                errs.append(f"{w}: news story with a single media source must add the 'single' (单一来源) tag")
        for b in briefs:
            w = b.get("id", "?")
            if w in ids:
                errs.append(f"{w}: duplicate id")
            ids.add(w)
            id_sec[w] = k
            if not b.get("title") or not b.get("text"):
                errs.append(f"{w}: brief needs title and text")
            lim(errs, w, b.get("title"), "brief_title", "brief title")
            lim(errs, w, b.get("text"), "brief_text", "brief text")
            check_tags(w, b.get("tags"), k, errs, False)
            check_sources(w, b.get("sources"), errs)
    if total > LIM["stories_max"]:
        errs.append(f"要闻 total {total} > {LIM['stories_max']}")
    elif total < LIM["stories_min"]:
        warns.append(f"要闻 total {total} < {LIM['stories_min']} (OK only if sections are genuinely thin)")

    top = data.get("top3") or []
    if len(top) != 3:
        errs.append(f"top3: exactly 3 items required, got {len(top)}")
    cross = False
    for i, t in enumerate(top, 1):
        w = f"top3[{i}]"
        for f, key in (("lead", "top_lead"), ("fact", "top_fact"), ("analysis", "top_an")):
            if not (t.get(f) or "").strip():
                errs.append(f"{w}.{f}: required")
            lim(errs, f"{w}.{f}", t.get(f), key)
        refs = t.get("refs") or []
        if not refs:
            errs.append(f"{w}.refs: link at least one item id")
        for r in refs:
            if r not in ids:
                errs.append(f"{w}.refs: unknown id {r!r}")
        if len({id_sec.get(r) for r in refs if r in id_sec}) >= 2:
            cross = True
    if top and not cross:
        errs.append("top3: at least one item must synthesise across sections (refs from ≥2 sections)")

    for i, c in enumerate(data.get("corrections") or [], 1):
        if not c.get("text"):
            errs.append(f"corrections[{i}]: text required")
        check_sources(f"corrections[{i}]", [c.get("source")] if c.get("source") else [], errs)

    # global prose checks
    pats = blocked_patterns()
    if not pats:
        warns.append("blocked-patterns file missing: personal-name check skipped")
    body_han = 0
    for where, text in all_text(data):
        if not text:
            continue
        if not where.endswith(".org") and not where.endswith("source.name"):
            body_han += han(text)
        if URL_RE.search(text):
            errs.append(f"{where}: bare URL in prose — put links in sources: {text[:50]}")
        for rx in PROCESS_NOTES:
            m = re.search(rx, text)
            if m:
                errs.append(f"{where}: process note '{m.group(0)}' does not belong in reader text: {text[:50]}")
        for j in JARGON:
            if j in text:
                errs.append(f"{where}: jargon '{j}' (EDITORIAL_SPEC §7)")
    blob = json.dumps(data, ensure_ascii=False)
    for rx in pats:
        if rx.search(blob):
            errs.append("personal info: data matches a blocked pattern (user name/email) — remove it")
    if body_han > LIM["body_han"]:
        errs.append(f"body {body_han} 汉字 > {LIM['body_han']}")

    # light dedupe against the previous 3 data files
    if path:
        prev = sorted(p for p in path.parent.glob("????-??-??.json") if p.stem < d)[-3:]
        seen = {}
        for p in prev:
            try:
                for k in SEC_KEYS:
                    for it in (json.loads(p.read_text())["sections"].get(k) or {}).get("stories", []):
                        for s in it.get("sources", []):
                            seen[s.get("url")] = p.stem
            except Exception:
                pass
        for k in SEC_KEYS:
            for st in (data["sections"].get(k) or {}).get("stories", []):
                for s in st.get("sources", []):
                    if s.get("url") in seen and not st.get("prev"):
                        warns.append(f"{st['id']}: source already used on {seen[s['url']]}; add '前情' (prev) or drop")

    if html_path:
        check_html(Path(html_path), errs, pats)
    data["_stats"] = {"stories": total, "body_han": body_han}
    return errs, warns


def check_html(p: Path, errs: list, pats=None) -> None:
    raw = p.read_text(encoding="utf-8")
    body = raw.split("</head>", 1)[-1]
    visible = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", body, flags=re.S)
    visible = re.sub(r"<[^>]+>", " ", visible)
    if URL_RE.search(visible):
        errs.append(f"{p.name}: bare URL visible in page text: {URL_RE.search(visible).group(0)[:60]}")
    for rx in pats if pats is not None else blocked_patterns():
        if rx.search(raw):
            errs.append(f"{p.name}: page contains blocked personal info")


def main(argv: list[str]) -> int:
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 2
    path = Path(argv[0])
    html_path = Path(argv[argv.index("--html") + 1]) if "--html" in argv else None
    try:
        data = load(path)
    except Exception as e:  # noqa: BLE001
        print(f"ERROR cannot read {path}: {e}", file=sys.stderr)
        return 1
    errs, warns = validate(data, path, html_path)
    for w in warns:
        print(f"WARN  {w}")
    for e in errs:
        print(f"ERROR {e}", file=sys.stderr)
    st = data.get("_stats", {})
    status = "FAIL" if errs else "PASS"
    print(f"{status}: {path.name} — {st.get('stories')} 条要闻, 正文 {st.get('body_han')} 汉字, "
          f"{len(errs)} error(s), {len(warns)} warning(s)")
    return 1 if errs else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
