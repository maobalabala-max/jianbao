#!/usr/bin/env python3
"""Draft the combined briefing's AI section from the same-day AI daily report.

usage: python3 tools/excerpt_ai.py YYYY-MM-DD [--n 3] [--merge DATA.json] [--force]
       [--reports /workspace/ai-daily/reports]

- Reads /workspace/ai-daily/reports/YYYY-MM-DD.md, takes the first N (2–3) stories of「重点消息」
  (the report orders them by significance), maps legacy evidence tags to the unified set and fills
  title / lede / detail / why / watch / sources / ai_anchor (story-N on the AI page).
- Prints the JSON, or with --merge writes it into DATA.json → sections.ai (refuses to overwrite
  existing AI stories unless --force).
- Fields are cut at sentence boundaries; anything still over the limits is reported here and by the
  validator — edit those fields by hand (titles in particular usually need rewriting to ≤28 字).
- With --merge, a missing DATA.json is first created as an empty skeleton (date/summary/top3/4 sections/
  corrections), so this is also the "start a new issue" command.
- Exit 3 when the report does not exist: write the AI section yourself (EDITORIAL_SPEC §AI 栏兜底).
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from briefing_common import LEGACY_TAG_MAP, host_name, zlen  # noqa: E402
from validate_briefing import LIM  # noqa: E402

REPORTS = Path("/workspace/ai-daily/reports")
FIELD_RE = re.compile(r"^(?:\*\*)?(事实|来源与证据|来源|为什么值得关注|为什么重要|新增与疑点|疑点|看点|接下来关注)(?:\*\*)?[：:]\s*(.*)$")


def sentences(text: str) -> list[str]:
    return [s for s in re.split(r"(?<=[。；！？])", text.strip()) if s.strip()]


def clip(text: str, limit: float) -> str:
    out = ""
    for s in sentences(text):
        if out and zlen(out + s) > limit:
            break
        out += s
    out = out.strip()
    if out.endswith("；"):
        out = out[:-1] + "。"
    return out


def parse_report(md: str) -> list[dict]:
    m = re.search(r"(?ms)^## 重点消息\s*$(.*?)(?=^## |\Z)", md)
    if not m:
        return []
    stories = []
    for chunk in re.split(r"(?m)^###\s+", m.group(1))[1:]:
        head, _, body = chunk.partition("\n")
        tags = re.findall(r"【([^】]+)】", head)
        title = re.sub(r"【[^】]+】", "", head).strip()
        fields, cur = {}, None
        for ln in body.splitlines():
            fm = FIELD_RE.match(ln.strip())
            if fm:
                cur = fm.group(1)
                fields.setdefault(cur, [])
                if fm.group(2):
                    fields[cur].append(fm.group(2))
            elif cur and ln.strip():
                fields[cur].append(ln.strip())
        stories.append({"title": title, "tags": tags, "fields": fields})
    return stories


def to_item(s: dict, n: int) -> dict:
    f = s["fields"]
    facts = [re.sub(r"^[-*]\s*", "", x) for x in f.get("事实", [])]
    srcs = []
    for x in f.get("来源与证据", []) + f.get("来源", []):
        x = re.sub(r"^[-*]\s*", "", x)
        um = re.search(r"https?://\S+", x)
        if not um:
            continue
        name = re.sub(r"[：:]\s*$", "", x[: um.start()].strip()) or host_name(um.group(0))
        srcs.append({"name": name, "url": um.group(0).rstrip("）)。，,")})
    tags = []
    for t in s["tags"]:
        k = LEGACY_TAG_MAP.get(t.strip())
        if k and k != "an" and k not in tags:
            tags.append(k)
    if not tags:
        tags = ["media"]
    if any("付费" in x["name"] for x in srcs) and "media" in tags:
        tags[tags.index("media")] = "paywall"
    if len(srcs) == 1 and any(t in tags for t in ("media", "paywall", "rumor")):
        tags.append("single")
    why = " ".join(f.get("为什么值得关注", []) + f.get("为什么重要", []))
    watch = " ".join(f.get("看点", []) + f.get("接下来关注", []))
    title = s["title"]
    if zlen(title) > LIM["title"] and "：" in title:
        title = title.split("：", 1)[0] if zlen(title.split("：", 1)[0]) >= 8 else title
    return {
        "tags": tags[:3],
        "org": (srcs[0]["name"] if srcs else "AI 日报"),
        "title": title,
        "lede": clip(facts[0] if facts else "", LIM["lede"]),
        "detail": clip(" ".join(facts[1:3]), LIM["detail"]) if len(facts) > 1 else "",
        "why": clip(why, LIM["why"]),
        "why_analysis": True,
        "watch": clip(watch, LIM["watch"]) or None,
        "sources": srcs[:3],
        "ai_anchor": f"story-{n}",
    }


def skeleton(d: str) -> dict:
    return {
        "date": d,
        "summary": "",
        "top3": [],
        "sections": {k: {"stories": [], "briefs": []} for k in ("ai", "sci", "tech", "lon")},
        "corrections": [],
    }


def main(argv: list[str]) -> int:
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 2
    d = argv[0]
    n = int(argv[argv.index("--n") + 1]) if "--n" in argv else 3
    reports = Path(argv[argv.index("--reports") + 1]) if "--reports" in argv else REPORTS
    rp = reports / f"{d}.md"
    if "--merge" in argv:  # create the day's data skeleton on first use
        dp0 = Path(argv[argv.index("--merge") + 1])
        if not dp0.exists():
            dp0.parent.mkdir(parents=True, exist_ok=True)
            dp0.write_text(json.dumps(skeleton(d), ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
            print(f"created skeleton {dp0}", file=sys.stderr)
    if not rp.exists():
        print(f"NO-AI-REPORT: {rp} not found — write the AI section by hand (2–3 items, own sources, "
              f"no ai_anchor); the page will link /ai/ instead.", file=sys.stderr)
        return 3
    items = [to_item(s, i) for i, s in enumerate(parse_report(rp.read_text(encoding="utf-8"))[: max(2, min(3, n))], 1)]
    if not items:
        print(f"ERROR no「重点消息」stories parsed from {rp}", file=sys.stderr)
        return 1
    for i, it in enumerate(items, 1):
        for k in ("title", "lede", "detail", "why", "watch"):
            if it.get(k) and zlen(it[k]) > LIM[k]:
                print(f"EDIT  AI item {i} {k}: {zlen(it[k]):g} 字 > {LIM[k]} — rewrite by hand", file=sys.stderr)
            if k in ("lede", "why") and not it.get(k):
                print(f"EDIT  AI item {i} {k}: empty — fill by hand", file=sys.stderr)
    if "--merge" in argv:
        dp = Path(argv[argv.index("--merge") + 1])
        data = json.loads(dp.read_text(encoding="utf-8")) if dp.exists() else {"date": d, "sections": {}}
        ai = data.setdefault("sections", {}).setdefault("ai", {})
        if ai.get("stories") and "--force" not in argv:
            print(f"ERROR {dp} already has AI stories; use --force to replace", file=sys.stderr)
            return 1
        ai["stories"] = items
        ai["from_ai_daily"] = True
        dp.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print(f"merged {len(items)} AI item(s) into {dp}")
    else:
        print(json.dumps(items, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
