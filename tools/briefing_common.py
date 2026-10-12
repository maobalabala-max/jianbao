"""Shared helpers for the v2 briefing tools (combined briefing + AI daily).

Imported by tools/gen_briefing.py, tools/validate_briefing.py, tools/excerpt_ai.py
and by /workspace/ai-daily/publish_ai_daily.py. Pure stdlib.
"""
from __future__ import annotations

import hashlib
import html
import re
from pathlib import Path
from urllib.parse import urlparse

SITE = Path(__file__).resolve().parent.parent  # /workspace/briefing-site
CSS_PATH = SITE / "assets" / "briefing.css"
SITE_URL = "https://jianbao.space"
WEEKDAY = "一二三四五六日"

# ---- unified evidence tag set (EDITORIAL_SPEC §5) --------------------------
EVIDENCE_TAGS = {
    "off": "官方/一手",
    "peer": "同行评审",
    "pre": "预印本",
    "media": "媒体报道",
    "cross": "独立交叉确认",
    "paywall": "付费报道·二手转述",
    "rumor": "推断/传闻",
}
SUBJECT_TAGS = {
    "mouse": "动物实验",
    "cell": "细胞实验",
    "human": "人群·观察性",
    "rct": "人体·RCT",
}
FLAG_TAGS = {"single": "单一来源"}
ALL_TAGS = {**EVIDENCE_TAGS, **SUBJECT_TAGS, **FLAG_TAGS}
# legacy AI-daily labels → unified keys
LEGACY_TAG_MAP = {
    "公开材料可核对": "off", "官方/一手": "off", "官方": "off",
    "原创媒体报道": "media", "媒体报道": "media",
    "独立交叉确认": "cross",
    "早期信号／传闻": "rumor", "早期信号/传闻": "rumor", "推断/传闻": "rumor", "传闻": "rumor",
    "分析／推断": "an", "分析/推断": "an", "分析": "an",
    "付费报道·二手转述": "paywall", "同行评审": "peer", "预印本": "pre",
}

SECTIONS = [  # key, short name (chip), full name
    ("ai", "AI", "AI 与大模型"),
    ("sci", "科学", "科学、物理与复杂性"),
    ("tech", "科技", "互联网与科技产业"),
    ("lon", "抗衰", "抗衰老与长寿"),
]
SECTION_LIMITS = {"ai": (0, 3), "sci": (0, 3), "tech": (0, 3), "lon": (0, 2)}

# words that read as process notes, not news (EDITORIAL_SPEC §7)
PROCESS_NOTES = [r"(?<![\d.])40[34](?![\d.])(?!\s*(?:项|个|人|万|亿|家|条|篇|名|号|年|米|公里|天|种|例|只|台|款|位|%))",
                 "无法抓取", "抓取失败", "未能打开", "打不开", "本环境", "自行统计", "下期跟进", "稍候更新",
                 "稍后更新", "日报延迟", "今日延迟", "未能产出", "未产出", "页面无法", "检索失败", "工具报错"]
JARGON = ["叙事", "同窗口", "三线", "口径", "托管面", "加码", "赋能", "抓手"]
BANNED_HOSTS = ["socastsrm.com"]  # syndication mirrors, not originals

URL_RE = re.compile(r"(https?://|www\.)\S+", re.I)


def zlen(s: str) -> float:
    """Chinese-typesetting length: CJK/full-width = 1, ASCII = 0.5, whitespace = 0."""
    n = 0.0
    for c in s or "":
        if c.isspace():
            continue
        n += 0.5 if ord(c) < 128 else 1
    return n


def han(s: str) -> int:
    return len(re.findall(r"[\u3400-\u9fff]", s or ""))


def strip_tags(s: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", "", s or ""))


def reading_minutes(text: str) -> float:
    t = strip_tags(text)
    words = len(re.findall(r"[A-Za-z0-9][A-Za-z0-9.\-+/%$]*", t))
    return han(t) / 400 + words / 200


def blocked_patterns(site: Path = SITE) -> list[re.Pattern]:
    """Private personal-info patterns (same file the pre-commit hook uses; never stored in repo)."""
    out = []
    for gitdir in (site / ".git", SITE / ".git"):
        f = gitdir / "info" / "blocked-patterns"
        if f.is_file():
            for ln in f.read_text(encoding="utf-8").splitlines():
                ln = ln.strip()
                if ln and not ln.startswith("#"):
                    out.append(re.compile(ln, re.I))
            break
    return out


def css_href(site: Path = SITE) -> str:
    p = site / "assets" / "briefing.css"
    if not p.exists():
        p = CSS_PATH
    v = hashlib.sha1(p.read_bytes()).hexdigest()[:8]
    return f"/assets/briefing.css?v={v}"


def tag_html(keys) -> str:
    out = []
    for k in keys:
        if k == "an":
            out.append('<span class="tag t-an">分析</span>')
        elif k in ALL_TAGS:
            out.append(f'<span class="tag t-{k}">{ALL_TAGS[k]}</span>')
        else:
            out.append(f'<span class="tag t-other">{html.escape(str(k))}</span>')
    return "".join(out)


HOST_NAMES = {
    "github.com": "GitHub", "openai.com": "OpenAI", "help.openai.com": "OpenAI 帮助中心",
    "community.openai.com": "OpenAI 开发者社区", "anthropic.com": "Anthropic", "blog.google": "Google 博客",
    "theverge.com": "The Verge", "techcrunch.com": "TechCrunch", "newscientist.com": "New Scientist",
    "scientificamerican.com": "Scientific American", "washingtonpost.com": "华盛顿邮报",
    "theinformation.com": "The Information", "wsj.com": "WSJ", "bloomberg.com": "Bloomberg",
    "reuters.com": "Reuters", "ft.com": "FT", "nytimes.com": "NYT", "theguardian.com": "Guardian",
    "abc.net.au": "ABC", "huggingface.co": "Hugging Face", "mistral.ai": "Mistral", "docs.mistral.ai": "Mistral 文档",
    "arxiv.org": "arXiv", "nature.com": "Nature", "science.org": "Science", "doi.org": "DOI",
    "aws.amazon.com": "AWS", "blogs.windows.com": "Windows 博客", "siliconangle.com": "SiliconANGLE",
    "finance.yahoo.com": "Yahoo Finance", "x.com": "X", "twitter.com": "X", "cnbc.com": "CNBC",
    "axios.com": "Axios", "semafor.com": "Semafor", "venturebeat.com": "VentureBeat", "arstechnica.com": "Ars Technica",
}


def host_name(url: str) -> str:
    h = urlparse(url).netloc.lower()
    h = h[4:] if h.startswith("www.") else h
    if h in HOST_NAMES:
        return HOST_NAMES[h]
    parts = h.split(".")
    for i in range(len(parts) - 1):
        cand = ".".join(parts[i:])
        if cand in HOST_NAMES:
            return HOST_NAMES[cand]
    return h


def date_cn(d) -> str:
    return f"{d.year}年{d.month}月{d.day}日 周{WEEKDAY[d.weekday()]}"


def dated_pages(dirpath: Path) -> list[Path]:
    return sorted(p for p in dirpath.glob("*.html") if re.fullmatch(r"\d{4}-\d{2}-\d{2}", p.stem))


def bar_html(chips: str, links: list[tuple[str, str, bool]], brand: bool = False) -> str:
    """Sticky top bar: [brand → /] section chips on the left, nav links on the right.
    The feed link gets class="opt" so it can be hidden on narrow screens (it is also in the footer)."""
    lk = "".join(f'<a href="{html.escape(h)}"{" class=\"opt\"" if h == "/feed.xml" else ""}'
                 f'{" aria-current=\"page\"" if cur else ""}>{html.escape(t)}</a>'
                 for t, h, cur in links)
    left = '<a class="brand" href="/">每日简报</a>' if brand else ""
    return (f'<nav class="bar" aria-label="导航"><div class="bar-in">{left}'
            f'<div class="chips">{chips}</div><div class="links">{lk}</div></div></nav>')


HEAD_ICONS = ('<link rel="icon" href="/favicon.ico" sizes="any">\n'
              '  <link rel="icon" href="/favicon.svg" type="image/svg+xml">\n'
              '  <link rel="apple-touch-icon" href="/apple-touch-icon.png">')


# ---- homepage / archive list (design B "卡片", 2026-10-08) -----------------
def _md(d) -> str:
    return f"{d.month}月{d.day}日"


def week_archive_html(items: list[dict], side_label: str, side_missing: str = "", side_class: str = "ai") -> str:
    """Week-grouped archive rows shared by /, /page/N.html and /ai/.

    items: dicts with d (date), href, blurb, side (same-day companion href or None).
    Companion pill only renders when side is present (no empty dash). Week ranges use the
    dates actually on this page, so a week split across pages shows the partial span.
    Month banners appear when the month of a week's newest entry changes.
    """
    import datetime as _dt  # local: avoid a top-level datetime import in this module
    if not items:
        return '<p class="hm-empty">暂无往期。</p>'
    groups: list[tuple[tuple[int, int], list[dict]]] = []
    for e in items:
        wk = tuple(e["d"].isocalendar()[:2])
        if not groups or groups[-1][0] != wk:
            groups.append((wk, []))
        groups[-1][1].append(e)
    out: list[str] = []
    prev_month: tuple[int, int] | None = None
    for _wk, rows in groups:
        first, last = rows[0]["d"], rows[-1]["d"]  # newest-first within the week
        lo, hi = last, first
        mkey = (hi.year, hi.month)
        if mkey != prev_month:
            out.append(f'<p class="hm-month"><span>{mkey[0]}</span>{mkey[1]} 月</p>')
            prev_month = mkey
        if lo == hi:
            rng = _md(lo)
        elif lo.month == hi.month:
            rng = f"{lo.month}月{lo.day}日 – {hi.day}日"
        else:
            rng = f"{_md(lo)} – {_md(hi)}"
        n_side = sum(1 for e in rows if e.get("side"))
        lis = []
        for e in rows:
            d = e["d"]
            side = (
                f'<a class="hm-pill hm-{side_class}" href="{html.escape(e["side"])}" '
                f'title="同日 {side_label}">{side_label}</a>'
                if e.get("side") else ""
            )
            blurb = (e.get("blurb") or "").strip() or "（无摘要）"
            lis.append(
                f'<li{" class=\"has-side\"" if e.get("side") else ""}>'
                f'<a class="hm-main" href="{html.escape(e["href"])}">'
                f'<span class="hm-d"><b>{d.month:02d}.{d.day:02d}</b>'
                f'<small>周{WEEKDAY[d.weekday()]}</small></span>'
                f'<span class="hm-b">{html.escape(blurb)}</span></a>'
                f'<span class="hm-st">{side}</span></li>'
            )
        sp = " " if side_label[:1].isascii() else ""
        cnt = f"{len(rows)} 期" + (f" · {n_side} 期有{sp}{side_label}" if n_side else "")
        out.append(
            f'<section class="hm-week">'
            f'<header class="hm-wh"><h3>{rng}</h3><span>{cnt}</span></header>'
            f'<ul class="hm-rows">{"".join(lis)}</ul></section>'
        )
    return "\n".join(out)
