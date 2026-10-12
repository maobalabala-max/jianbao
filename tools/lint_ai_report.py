#!/usr/bin/env python3
"""Lint an AI daily Markdown report (/workspace/ai-daily/reports/D.md) against PROMPT.md §六.

Usage: lint_ai_report.py YYYY-MM-DD [--reports DIR]   (or a path to the .md file)
Exit 1 on errors. Checks: 2,500 汉字 hard cap (URLs excluded), no URLs outside
"机构名：URL" source lines, unified tags (1–2 per item), no process notes outside
「本期说明」, 更新与纠错 items must reference an earlier date, no user name.
"""
from __future__ import annotations
import argparse, re, sys
from pathlib import Path
sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from briefing_common import LEGACY_TAG_MAP, PROCESS_NOTES, JARGON, URL_RE, han, blocked_patterns  # noqa: E402

CAP = 2500
SOURCE_LINE = re.compile(r"^\s*[-*]?\s*[^：:\s][^：]{0,60}[：:]\s*<?https?://\S+>?\s*$")
TAG_RE = re.compile(r"【([^】]+)】")
DATE_REF = re.compile(r"(报道|更正|纠正|勘误|此前|上期|前期|补充|仍未|已于)")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("report")
    ap.add_argument("--reports", default="/workspace/ai-daily/reports")
    a = ap.parse_args()
    p = Path(a.report)
    if not p.exists():
        p = Path(a.reports) / f"{a.report}.md"
    if not p.exists():
        print(f"FAIL: no report at {p}")
        return 2
    text = p.read_text(encoding="utf-8")
    errs: list[str] = []
    warns: list[str] = []

    section = ""
    body_for_count: list[str] = []
    for no, line in enumerate(text.splitlines(), 1):
        h2 = re.match(r"^##\s+(.+?)\s*$", line)
        if h2:
            section = h2.group(1)
        in_notes = section.startswith("本期说明") or (section == "" and not line.startswith("#"))
        stripped = URL_RE.sub("", line)
        if not in_notes:
            body_for_count.append(stripped)
        # URLs only in "机构名：URL" lines (sources / 简讯 endings may carry name：URL at line end)
        if URL_RE.search(line) and not SOURCE_LINE.match(line):
            tail_ok = re.search(r"[^\s：:]{2,}[：:]\s*https?://\S+\s*$", line) and len(URL_RE.findall(line)) == 1
            if not tail_ok:
                errs.append(f"L{no}: bare URL / URL inside prose — use '机构名：URL' on its own line: {line.strip()[:70]}")
        if line.startswith("### "):
            tags = TAG_RE.findall(line)
            keys = []
            for t in tags:
                k = LEGACY_TAG_MAP.get(t.strip())
                if not k:
                    errs.append(f"L{no}: tag 【{t}】 not in the unified set (PROMPT.md §四)")
                else:
                    keys.append(k)
            if not tags and not section.startswith(("更新", "实务")):
                errs.append(f"L{no}: item has no evidence tag")
            ev = [k for k in keys if k != "an"]
            if len(ev) > 2 or len(tags) > 3:
                errs.append(f"L{no}: too many tags ({len(tags)}); use 1–2 evidence tags (+【分析】)")
            if "rumor" in keys and {"off", "cross"} & set(keys):
                errs.append(f"L{no}: contradictory tags {tags}")
            if "rumor" in keys and section.startswith("重点"):
                warns.append(f"L{no}: 【推断/传闻】 item in 重点消息 — move it to 早期信号")
        if not in_notes:
            for rx in PROCESS_NOTES:
                m = re.search(rx, stripped)
                if m:
                    errs.append(f"L{no}: process note '{m.group(0)}' in body — move to「本期说明」: {line.strip()[:60]}")
            for j in JARGON:
                if j in stripped:
                    warns.append(f"L{no}: jargon '{j}'")
        if section.startswith("更新") and re.match(r"^\s*([-*]|###)\s+", line) and not DATE_REF.search(line):
            warns.append(f"L{no}: 更新与纠错 item without the original report date — is it really an update? {line.strip()[:50]}")
    for rx in blocked_patterns():
        if rx.search(text):
            errs.append("personal info: report matches a blocked pattern (user name/email) — remove it")
    n = han("\n".join(body_for_count))
    if n > CAP:
        errs.append(f"length: {n} 汉字 > {CAP} hard cap (URLs and 本期说明 excluded)")
    for w in warns:
        print("WARN ", w)
    for e in errs:
        print("ERROR", e)
    print(f"{'FAIL' if errs else 'PASS'}: {p.name} — {n} 汉字, {len(errs)} error(s), {len(warns)} warning(s)")
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
