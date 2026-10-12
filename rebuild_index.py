#!/usr/bin/env python3
"""Regenerate archive index pages from dated briefing files YYYY/YYYY-MM-DD.html.

Styling comes from /assets/briefing.css (v2 design, shared with daily pages); helpers in tools/briefing_common.py.
Ends by running build_site_meta.py (og tags, feed.xml, sitemap.xml, robots.txt)."""
from pathlib import Path
import math
import re
import html
import datetime
import shutil

ROOT = Path(__file__).resolve().parent
WEEKDAY = "一二三四五六日"
PER_PAGE = 14  # ~12–16 entries per page

import sys as _sys
_sys.dont_write_bytecode = True
_sys.path.insert(0, str(ROOT / "tools"))
from briefing_common import HEAD_ICONS, SECTIONS, bar_html, css_href, week_archive_html  # noqa: E402  (shared v2 design helpers)
import validate_briefing as V  # noqa: E402  (data-file loader: assigns story ids)
import os  # noqa: E402

DATA_DIR = Path(os.environ.get("BRIEFING_DATA_DIR", "/workspace/daily-briefing/data"))  # per-day JSON (outside the repo)


def collect_entries():
    entries = []
    for path in sorted(
        ROOT.glob("[0-9][0-9][0-9][0-9]/[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9].html"),
        reverse=True,
    ):
        date_s = path.stem
        dt = datetime.date.fromisoformat(date_s)
        text = path.read_text(encoding="utf-8")
        lede_m = re.search(r'<p class="lede">(.*?)</p>', text, re.S)
        lede = re.sub("<[^>]+>", "", lede_m.group(1) if lede_m else "")
        lede = html.unescape(re.sub(r"\s+", " ", lede)).strip()
        year = path.parent.name
        entries.append({
            "href": f"/{year}/{path.name}",
            "iso": date_s,
            "dt": dt,
            "label": f"{dt.year}年{dt.month}月{dt.day}日",
            "dow": f"周{WEEKDAY[dt.weekday()]}",
            "month_key": (dt.year, dt.month),
            "month_label": f"{dt.year}年{dt.month}月",
            "lede": lede,
            "ai": f"/ai/{date_s}.html" if (ROOT / "ai" / f"{date_s}.html").exists() else None,
        })
    return entries


LEAD_PREFIX = re.compile(r"^(今天的主线|今日主线|周[一二三四五六日]主线|周末三天的主线|本周主线)[：:]\s*")


def render_cards(page_entries):
    """Week-grouped archive rows with the same-day AI daily indicator (homepage design B)."""
    items = [{"d": e["dt"], "href": e["href"], "blurb": LEAD_PREFIX.sub("", e["lede"]), "side": e["ai"]}
             for e in page_entries]
    return week_archive_html(items, "AI 日报", "当日没有 AI 日报")


def latest_hero(e):
    """Page-1 hero: latest issue card. 今日三件事 only when that day's data file exists."""
    d = e["dt"]
    page = (ROOT / e["href"].lstrip("/")).read_text(encoding="utf-8")
    meta = re.search(r'<p class="meta">(.*?)</p>', page, re.S)
    meta_t = re.sub(r"<[^>]+>", " ", meta.group(1)) if meta else ""
    bits = []
    m = re.search(r"阅读约\s*(\d+)\s*分钟", meta_t)
    if m:
        bits.append(f"阅读约 {m.group(1)} 分钟")
    m = re.search(r"(\d+)\s*条要闻\s*·\s*(\d+)\s*条简讯", meta_t)
    if m:
        bits += [f"{m.group(1)} 条要闻", f"{m.group(2)} 条简讯"]
    cards = ""
    dp = DATA_DIR / f'{e["iso"]}.json'
    if dp.exists() and 'content="briefing-v2"' in page:
        try:
            data = V.load(dp)
            sec_of = {}
            for k, _short, _full in SECTIONS:
                sec = data.get("sections", {}).get(k) or {}
                for it in (sec.get("stories") or []) + (sec.get("briefs") or []):
                    sec_of[it.get("id")] = k
            short = {k: sh for k, sh, _f in SECTIONS}
            cs = []
            for i, t in enumerate(data.get("top3") or [], 1):
                ks = []
                for r in t.get("refs") or []:
                    k = sec_of.get(r)
                    if k and k not in ks:
                        ks.append(k)
                pills = "".join(f'<span class="hm-tag k-{k}">{short[k]}</span>' for k in ks)
                ref = (t.get("refs") or [""])[0]
                cs.append(f'<a class="hm-card" href="{e["href"]}#{html.escape(ref)}"><span class="hm-lb">{pills}'
                          f'<span class="hm-n">0{i}</span></span><span class="hm-ct">{html.escape(t["lead"].rstrip("。"))}</span>'
                          f'<span class="hm-cf">{html.escape(t["fact"])}</span></a>')
            if cs:
                cards = f'<div class="hm-cards" aria-label="今日三件事">{"".join(cs)}</div>'
        except Exception as exc:  # never break the index over a bad data file
            print(f"WARN  hero: skipped 今日三件事 ({exc})")
    ai_btn = ""
    if e["ai"]:
        ap = (ROOT / e["ai"].lstrip("/")).read_text(encoding="utf-8")
        m = re.search(r"(\d+)\s*条重点", re.sub(r"<[^>]+>", " ", ap.split("</head>", 1)[-1]))
        ai_btn = f'<a class="hm-btn hm-btn2" href="{e["ai"]}">今日 AI 日报{" · " + m.group(1) + " 条重点" if m else ""}</a>'
    meta_html = "".join(f"<span>{b}</span>" for b in bits)
    return f"""    <article class="hm-hero">
      <div class="hm-spectrum" aria-hidden="true"><i></i><i></i><i></i><i></i></div>
      <div class="hm-in">
        <p class="hm-hrow"><span class="hm-date">{d.month:02d}.{d.day:02d}<small>{e["dow"]} · {d.year}</small></span><span class="hm-badge">最新一期</span></p>
        <h2 class="hm-sum"><a href="{e["href"]}">{html.escape(LEAD_PREFIX.sub("", e["lede"]))}</a></h2>
        {f'<p class="hm-meta">{meta_html}</p>' if meta_html else ""}
        {cards}
        <p class="hm-actions"><a class="hm-btn" href="{e["href"]}">阅读本期 →</a>{ai_btn}</p>
      </div>
    </article>"""


def page_href(page_num):
    if page_num <= 1:
        return "/"
    return f"/page/{page_num}.html"


ARROW_L = ('<svg class="pg-ic" viewBox="0 0 16 16" width="16" height="16" aria-hidden="true" focusable="false">'
           '<path d="M10 3.5 5.5 8l4.5 4.5" fill="none" stroke="currentColor" stroke-width="1.7" '
           'stroke-linecap="round" stroke-linejoin="round"/></svg>')
ARROW_R = ('<svg class="pg-ic" viewBox="0 0 16 16" width="16" height="16" aria-hidden="true" focusable="false">'
           '<path d="M6 3.5 10.5 8 6 12.5" fill="none" stroke="currentColor" stroke-width="1.7" '
           'stroke-linecap="round" stroke-linejoin="round"/></svg>')


def page_window(page_num, total_pages):
    """Page numbers to show: always first/last, current ±1, gaps as None (… ellipsis)."""
    if total_pages <= 7:
        return list(range(1, total_pages + 1))
    keep = {1, total_pages, page_num - 1, page_num, page_num + 1}
    if page_num <= 4:
        keep |= {2, 3, 4, 5}
    if page_num >= total_pages - 3:
        keep |= {total_pages - 4, total_pages - 3, total_pages - 2, total_pages - 1}
    nums = sorted(n for n in keep if 1 <= n <= total_pages)
    out = []
    for n in nums:
        if out and n - out[-1] > 1:
            out.append(None)
        out.append(n)
    return out


def render_pager(page_num, total_pages, page_count=0):
    """Pagination control (homepage bottom + /page/N.html). Desktop: ‹ 上一页 · 1 2 3 · 下一页 ›;
    ≤560px: ‹ · 2 / 3 · › (numbers hidden). No JS."""
    if total_pages <= 1:
        return ""
    if page_num > 1:
        prev = (f'<a class="pg-btn pg-prev" href="{page_href(page_num - 1)}" rel="prev" '
                f'aria-label="上一页（第 {page_num - 1} 页）">{ARROW_L}<span class="pg-lb">上一页</span></a>')
    else:
        prev = f'<span class="pg-btn pg-prev is-off" aria-disabled="true">{ARROW_L}<span class="pg-lb">上一页</span></span>'
    if page_num < total_pages:
        nxt = (f'<a class="pg-btn pg-next" href="{page_href(page_num + 1)}" rel="next" '
               f'aria-label="下一页（第 {page_num + 1} 页）"><span class="pg-lb">下一页</span>{ARROW_R}</a>')
    else:
        nxt = f'<span class="pg-btn pg-next is-off" aria-disabled="true"><span class="pg-lb">下一页</span>{ARROW_R}</span>'
    nums = []
    for n in page_window(page_num, total_pages):
        if n is None:
            nums.append('<li class="pg-gap" aria-hidden="true">…</li>')
        elif n == page_num:
            nums.append(f'<li><span class="pg-n is-cur" aria-current="page">{n}</span></li>')
        else:
            nums.append(f'<li><a class="pg-n" href="{page_href(n)}" aria-label="第 {n} 页">{n}</a></li>')
    meta = (f'<span class="pg-pos">第 {page_num} / {total_pages} 页</span>'
            + (f'<span class="pg-pos"> · </span>本页 {page_count} 期' if page_count else ""))
    return (
        '    <nav class="pg" aria-label="往期分页">\n'
        f'      {prev}\n'
        f'      <ol class="pg-nums">{"".join(nums)}</ol>\n'
        f'      <span class="pg-compact"><b>{page_num}</b> / {total_pages}</span>\n'
        f'      {nxt}\n'
        '    </nav>\n'
        f'    <p class="pg-meta">{meta}</p>'
    )


def render_intro(page_num, entries_all, page_entries=None):
    if page_num > 1:
        pe = page_entries or []
        if pe:
            hi, lo = pe[0]["dt"], pe[-1]["dt"]
            if lo.year == hi.year and lo.month == hi.month:
                span = f"{lo.month}月{lo.day}日 – {hi.day}日"
            elif lo.year == hi.year:
                span = f"{lo.month}月{lo.day}日 – {hi.month}月{hi.day}日"
            else:
                span = f"{lo.year}年{lo.month}月{lo.day}日 – {hi.year}年{hi.month}月{hi.day}日"
            sub = f'{span} · {len(pe)} 期 · <a href="/">回到最新一期</a>'
        else:
            sub = '<a href="/">回到最新一期</a>'
        return (
            f'    <header class="hm-arch-head">'
            f'<p class="hm-eyebrow">往期</p>'
            f'<h1>第 {page_num} 页</h1>'
            f'<p class="hm-arch-sub">{sub}</p></header>'
        )
    n_ai = sum(1 for e in entries_all if e["ai"])
    first = entries_all[-1]["dt"] if entries_all else None
    since = ""
    if first:
        lab = (f"{first.month}.{first.day:02d}"
               if first.year == entries_all[0]["dt"].year
               else f"{first.year}.{first.month}.{first.day:02d}")
        since = f'<div><b>{lab}</b><span>收录自</span></div>'
    return (f'    <header class="hm-intro"><div><h1>每日简报</h1>'
            f'<p>AI、科学、科技业界、抗衰老——每天约 10 件事，事实与判断分开。</p></div>'
            f'<div class="hm-stat"><div><b>{len(entries_all)}</b><span>期简报</span></div>'
            f'<div><b>{n_ai}</b><span>期 AI 日报</span></div>{since}</div></header>')


def render_page(page_num, total_pages, page_entries, newest_href, entries_all=None):
    entries_all = entries_all or page_entries
    title = "每日简报" if page_num == 1 else f"每日简报 · 第 {page_num} 页"
    cards_html = render_cards(page_entries)
    pager_html = render_pager(page_num, total_pages, len(page_entries))
    hero = latest_hero(entries_all[0]) if page_num == 1 and entries_all else ""
    links = [("最新一期", newest_href, False), ("AI 日报", "/ai/", False), ("订阅", "/feed.xml", False)]
    arch_h = ('    <div class="hm-arch-h"><h2>往期</h2><p class="hm-legend"><i></i>有同日 AI 日报</p></div>'
              if page_num == 1 else "")
    body_cls = "idx home" + (" hm-arch-page" if page_num > 1 else "")
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
  <meta name="description" content="每日简报归档：覆盖 AI、科学、科技业界与抗衰论文。">
  <meta name="color-scheme" content="light dark">
  {HEAD_ICONS}
  <link rel="stylesheet" href="{css_href(ROOT)}">
</head>
<body class="{body_cls}">
{bar_html("", links, brand=True)}
<main class="hm">
{render_intro(page_num, entries_all, page_entries)}
{hero}
  <section class="hm-arch">
{arch_h}
{cards_html}
{pager_html}
  </section>
</main>
<footer class="hm-foot"><span>每日简报 · 共 {len(entries_all)} 期</span><span><a href="/feed.xml">Atom 订阅</a> · <a href="/ai/">AI 前沿情报日报</a></span></footer>
</body>
</html>
"""


def main():
    entries = collect_entries()
    total = len(entries)
    total_pages = max(1, math.ceil(total / PER_PAGE)) if total else 1
    newest_href = entries[0]["href"] if entries else "/"

    # Clean old page/ directory if present, then recreate when needed
    page_dir = ROOT / "page"
    if page_dir.exists():
        shutil.rmtree(page_dir)

    written = []
    for page_num in range(1, total_pages + 1):
        start = (page_num - 1) * PER_PAGE
        chunk = entries[start : start + PER_PAGE]
        html_out = render_page(page_num, total_pages, chunk, newest_href, entries)
        if page_num == 1:
            out_path = ROOT / "index.html"
        else:
            page_dir.mkdir(parents=True, exist_ok=True)
            out_path = page_dir / f"{page_num}.html"
        out_path.write_text(html_out, encoding="utf-8")
        written.append(str(out_path.relative_to(ROOT)))

    print(f"wrote {len(written)} page(s) with {total} entries ({PER_PAGE}/page):")
    for w in written:
        print(f"  {w}")

    # SEO/social tags on all pages + feed.xml / sitemap.xml / robots.txt (idempotent)
    import sys
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(ROOT))
    import build_site_meta
    build_site_meta.main()


if __name__ == "__main__":
    main()
