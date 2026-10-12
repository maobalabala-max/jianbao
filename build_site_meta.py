#!/usr/bin/env python3
"""Site metadata build step for jianbao.space (idempotent; safe to run after every publish).

- Injects SEO / social tags (description, canonical, Open Graph, Twitter card,
  Atom alternate link) into every combined briefing page (YYYY/YYYY-MM-DD.html),
  every AI daily page (ai/YYYY-MM-DD.html) and the index pages
  (index.html, page/N.html, ai/index.html). Tags live between
  <!-- site-meta:start --> / <!-- site-meta:end --> and are replaced on rerun.
- Writes feed.xml (Atom, latest 30 items from /YYYY/ and /ai/),
  sitemap.xml and robots.txt.

Called automatically by rebuild_index.py and by /workspace/ai-daily/publish_ai_daily.py.
"""
from __future__ import annotations

import datetime as dt
import html
import re
from pathlib import Path
from xml.sax.saxutils import escape as xml_escape

ROOT = Path(__file__).resolve().parent
SITE_URL = "https://jianbao.space"
SITE_NAME = "每日简报"
TZ = dt.timezone(dt.timedelta(hours=8))  # Asia/Shanghai
PUBLISH_TIME = dt.time(8, 0)  # weekday 08:00 Shanghai
FEED_LIMIT = 30
DESC_MAX = 120
OG_IMAGE = f"{SITE_URL}/icon-512.png"
MARK_START = "<!-- site-meta:start -->"
MARK_END = "<!-- site-meta:end -->"

DATE_RE = r"[0-9]{4}-[0-9]{2}-[0-9]{2}"
FALLBACK = {
    "briefing": "每日简报：覆盖 AI、科学、科技业界与抗衰论文。",
    "ai": "AI 前沿情报日报：事实与推断分开，宁缺毋滥。",
    "index": "每日简报归档：覆盖 AI、科学、科技业界与抗衰论文。",
    "ai-index": "AI 前沿情报日报归档：事实与推断分开，宁缺毋滥。",
}


# ---------------------------------------------------------------- discovery
def briefing_pages() -> list[Path]:
    return sorted(p for p in ROOT.glob("[0-9][0-9][0-9][0-9]/*.html") if re.fullmatch(DATE_RE, p.stem))


def ai_pages() -> list[Path]:
    return sorted(p for p in (ROOT / "ai").glob("*.html") if re.fullmatch(DATE_RE, p.stem))


def index_pages() -> list[Path]:
    out = [ROOT / "index.html"]
    out += sorted((ROOT / "page").glob("*.html"), key=lambda p: int(p.stem) if p.stem.isdigit() else 0)
    out.append(ROOT / "ai" / "index.html")
    return [p for p in out if p.exists()]


def url_path(p: Path) -> str:
    rel = p.relative_to(ROOT).as_posix()
    if rel == "index.html":
        return "/"
    if rel.endswith("/index.html"):
        return "/" + rel[: -len("index.html")]
    return "/" + rel


def kind_of(p: Path) -> str:
    rel = p.relative_to(ROOT).as_posix()
    if rel == "ai/index.html":
        return "ai-index"
    if rel == "index.html" or rel.startswith("page/"):
        return "index"
    if rel.startswith("ai/"):
        return "ai"
    return "briefing"


# ---------------------------------------------------------------- extraction
def strip_block(text: str) -> str:
    return re.sub(r"[ \t]*" + re.escape(MARK_START) + r".*?" + re.escape(MARK_END) + r"[ \t]*\n?", "", text, flags=re.S)


def plain(fragment: str) -> str:
    fragment = re.sub(r"<br\s*/?>|</li>", " ", fragment, flags=re.I)
    fragment = re.sub(r"<[^>]+>", "", fragment)
    return re.sub(r"\s+", " ", html.unescape(fragment)).strip()


def clip(s: str, n: int = DESC_MAX) -> str:
    return s if len(s) <= n else s[: n - 1].rstrip() + "…"


def page_title(text: str) -> str:
    m = re.search(r"<title>(.*?)</title>", text, re.S)
    return plain(m.group(1)) if m else SITE_NAME


def description(text: str, kind: str) -> str:
    body = text.split("</head>", 1)[-1]
    m = None
    if kind == "briefing":
        m = re.search(r'<p class="lede">(.*?)</p>', body, re.S)
    elif kind == "ai":
        m = re.search(r'<div class="lede">(.*?)</div>', body, re.S)
    desc = plain(m.group(1)) if m else ""
    return clip(desc) if desc else FALLBACK[kind]


def page_date(p: Path) -> dt.date | None:
    return dt.date.fromisoformat(p.stem) if re.fullmatch(DATE_RE, p.stem) else None


def stamp(d: dt.date) -> str:
    return dt.datetime.combine(d, PUBLISH_TIME, TZ).isoformat()


# ---------------------------------------------------------------- injection
def meta_block(p: Path, text: str) -> str:
    kind = kind_of(p)
    url = SITE_URL + url_path(p)
    title = page_title(text)
    desc = description(text, kind)
    is_article = kind in ("briefing", "ai")
    a = lambda s: html.escape(s, quote=True)  # noqa: E731
    lines = [
        MARK_START,
        f'<meta name="description" content="{a(desc)}">',
        f'<link rel="canonical" href="{a(url)}">',
        f'<link rel="alternate" type="application/atom+xml" title="{SITE_NAME} · 订阅" href="/feed.xml">',
        f'<meta property="og:site_name" content="{SITE_NAME}">',
        '<meta property="og:locale" content="zh_CN">',
        f'<meta property="og:type" content="{"article" if is_article else "website"}">',
        f'<meta property="og:title" content="{a(title)}">',
        f'<meta property="og:description" content="{a(desc)}">',
        f'<meta property="og:url" content="{a(url)}">',
        f'<meta property="og:image" content="{OG_IMAGE}">',
    ]
    d = page_date(p)
    if is_article and d:
        lines.append(f'<meta property="article:published_time" content="{stamp(d)}">')
    lines += [
        '<meta name="twitter:card" content="summary">',
        f'<meta name="twitter:title" content="{a(title)}">',
        f'<meta name="twitter:description" content="{a(desc)}">',
        MARK_END,
    ]
    return "".join(f"  {ln}\n" for ln in lines)


def inject(p: Path) -> bool:
    original = p.read_text(encoding="utf-8")
    text = strip_block(original)
    head, sep, rest = text.partition("</head>")
    if not sep:
        return False
    # drop stray tags the block now owns (e.g. template-generated description)
    head = re.sub(r'[ \t]*<meta name="description"[^>]*>[ \t]*\n?', "", head)
    head = re.sub(r'[ \t]*<link rel="canonical"[^>]*>[ \t]*\n?', "", head)
    head = re.sub(r'[ \t]*<link rel="alternate" type="application/(?:atom|rss)\+xml"[^>]*>[ \t]*\n?', "", head)
    text = head + sep + rest
    block = meta_block(p, text)
    m = re.search(r"<title>.*?</title>[ \t]*\n", text, re.S)
    if m:
        text = text[: m.end()] + block + text[m.end():]
    else:
        text = text.replace("</head>", block + "</head>", 1)
    if text != original:
        p.write_text(text, encoding="utf-8")
        return True
    return False


# ---------------------------------------------------------------- feed / sitemap / robots
def feed_items() -> list[dict]:
    items = []
    for kind, pages in (("briefing", briefing_pages()), ("ai", ai_pages())):
        for p in pages:
            text = p.read_text(encoding="utf-8")
            d = page_date(p)
            items.append({
                "date": d,
                "order": 0 if kind == "briefing" else 1,
                "title": page_title(text),
                "url": SITE_URL + url_path(p),
                "summary": description(text, kind),
                "category": "每日简报" if kind == "briefing" else "AI 前沿情报日报",
            })
    items.sort(key=lambda e: (e["date"], -e["order"]), reverse=True)
    return items[:FEED_LIMIT]


def build_feed() -> str:
    items = feed_items()
    updated = stamp(items[0]["date"]) if items else dt.datetime.now(TZ).replace(microsecond=0).isoformat()
    x = xml_escape
    out = [
        '<?xml version="1.0" encoding="utf-8"?>',
        '<feed xmlns="http://www.w3.org/2005/Atom" xml:lang="zh-CN">',
        f"  <title>{SITE_NAME}</title>",
        "  <subtitle>综合每日简报与 AI 前沿情报日报</subtitle>",
        f"  <id>{SITE_URL}/</id>",
        f'  <link rel="alternate" type="text/html" href="{SITE_URL}/"/>',
        f'  <link rel="self" type="application/atom+xml" href="{SITE_URL}/feed.xml"/>',
        f"  <updated>{updated}</updated>",
        f"  <author><name>{SITE_NAME}</name></author>",
        f"  <icon>{SITE_URL}/favicon-32.png</icon>",
    ]
    for e in items:
        ts = stamp(e["date"])
        out += [
            "  <entry>",
            f"    <title>{x(e['title'])}</title>",
            f'    <link rel="alternate" type="text/html" href="{x(e["url"])}"/>',
            f"    <id>{x(e['url'])}</id>",
            f"    <published>{ts}</published>",
            f"    <updated>{ts}</updated>",
            f'    <category term="{x(e["category"], {chr(34): "&quot;"})}"/>',
            f"    <summary>{x(e['summary'])}</summary>",
            "  </entry>",
        ]
    out.append("</feed>")
    return "\n".join(out) + "\n"


def build_sitemap() -> str:
    dated = [(p, page_date(p)) for p in briefing_pages() + ai_pages()]
    latest = max((d for _, d in dated), default=dt.date.today())
    latest_ai = max((page_date(p) for p in ai_pages()), default=latest)
    urls = []
    for p in index_pages():
        urls.append((url_path(p), latest_ai if kind_of(p) == "ai-index" else latest))
    for p, d in sorted(dated, key=lambda t: (t[1], url_path(t[0])), reverse=True):
        urls.append((url_path(p), d))
    out = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for path, d in urls:
        out.append(f"  <url><loc>{xml_escape(SITE_URL + path)}</loc><lastmod>{d.isoformat()}</lastmod></url>")
    out.append("</urlset>")
    return "\n".join(out) + "\n"


def build_robots() -> str:
    return f"User-agent: *\nAllow: /\n\nSitemap: {SITE_URL}/sitemap.xml\n"


def write_if_changed(p: Path, content: str) -> bool:
    if p.exists() and p.read_text(encoding="utf-8") == content:
        return False
    p.write_text(content, encoding="utf-8")
    return True


def main() -> int:
    pages = briefing_pages() + ai_pages() + index_pages()
    changed = [p for p in pages if inject(p)]
    outputs = {
        ROOT / "feed.xml": build_feed(),
        ROOT / "sitemap.xml": build_sitemap(),
        ROOT / "robots.txt": build_robots(),
    }
    written = [p for p, c in outputs.items() if write_if_changed(p, c)]
    print(f"site-meta: {len(pages)} page(s) checked, {len(changed)} updated; "
          f"{', '.join(p.name for p in written) or 'feed/sitemap/robots unchanged'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
