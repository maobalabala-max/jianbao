"""Static public pages for jianbao.space: /about.html and the auto-generated /corrections.html.

Called by rebuild_index.py (before build_site_meta). Idempotent: output depends only on the data
files, reports and pages on disk. Pure stdlib.

Corrections are collected from three places, newest first:
  1. combined briefing data files  DATA_DIR/YYYY-MM-DD.json  → "corrections": [{text, source}]
  2. combined pages without a data file: <aside class="corr"> blocks in /YYYY/YYYY-MM-DD.html
  3. AI daily reports  AI_REPORTS_DIR/YYYY-MM-DD.md, section 「更新与纠错」, bullets that start with
     「更正：」 or 「【更正】」 (ordinary follow-up updates in that section are NOT corrections)
"""
import html
import json
import os
import re
from datetime import date
from pathlib import Path

from briefing_common import (ALL_TAGS, EVIDENCE_TAGS, FLAG_TAGS, HEAD_ICONS, SECTIONS, SUBJECT_TAGS,
                             bar_html, css_href, date_cn, site_foot_html, subscribe_html, tag_html)

DATA_DIR = Path(os.environ.get("BRIEFING_DATA_DIR", "/workspace/daily-briefing/data"))
AI_REPORTS = Path(os.environ.get("AI_REPORTS_DIR", "/workspace/ai-daily/reports"))
DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
E = html.escape

TAG_NOTES = {
    "off": "公司公告、官方文档、论文原文、政府文件、财报等一手材料",
    "peer": "已在期刊发表、经过同行评审的论文",
    "pre": "arXiv、bioRxiv、medRxiv 等预印本，尚未经过同行评审",
    "media": "媒体的原创报道",
    "cross": "多个彼此独立的信源分别证实（多家转载同一独家不算）",
    "paywall": "原文在付费墙后，我们只读到摘要或其他媒体的转述",
    "rumor": "尚未证实的消息或推断；只放在简讯或「早期信号」里",
    "mouse": "研究对象是动物（多为小鼠）",
    "cell": "研究对象是细胞或组织",
    "human": "人群观察性研究（队列、横断面等），只能说明相关",
    "rct": "人体随机对照试验，证据等级最高",
    "single": "只有一个媒体或传闻来源，尚无第二个独立来源",
}


def page_shell(title: str, desc: str, body: str, current: str) -> str:
    links = [("每日简报", "/", False), ("AI 日报", "/ai/", False),
             ("关于", "/about.html", current == "about"), ("更正", "/corrections.html", current == "corr"),
             ("订阅", "/feed.xml", False)]
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{E(title)}</title>
  <meta name="color-scheme" content="light dark">
  {HEAD_ICONS}
  <link rel="stylesheet" href="{css_href()}">
</head>
<body class="idx home doc-page">
{bar_html("", links, brand=True)}
<main class="hm doc">
{body}
</main>
{site_foot_html()}
</body>
</html>
"""


# ------------------------------------------------------------------ about
def about_html() -> str:
    secs = "".join(f'<li><b class="doc-sec doc-{k}">{E(short)}</b>{E(full)}</li>' for k, short, full in SECTIONS)
    rows = []
    for group, tags in (("证据", EVIDENCE_TAGS), ("研究对象", SUBJECT_TAGS), ("提示", FLAG_TAGS)):
        for i, k in enumerate(tags):
            g = f'<th rowspan="{len(tags)}" scope="rowgroup">{group}</th>' if i == 0 else ""
            rows.append(f"<tr>{g}<td>{tag_html([k])}</td><td>{E(TAG_NOTES.get(k, ''))}</td></tr>")
    rows.append(f'<tr><th scope="rowgroup">判断</th><td>{tag_html(["an"])}</td>'
                f"<td>虚线标签，表示这是编辑的分析或推断，不是已核实的事实</td></tr>")
    body = f"""  <header class="hm-arch-head doc-head"><p class="hm-eyebrow">关于</p><h1>关于每日简报</h1>
    <p class="lede">一份写给普通读者的中文科技日报：每个工作日一期，用几分钟读完当天 AI、科学、科技产业和抗衰老研究里最值得知道的事，以及它们为什么重要。</p></header>

  <section class="doc-card"><h2>这里有什么</h2>
    <p>本站有两份互相链接的日报：</p>
    <ul class="doc-two">
      <li><a href="/"><b>综合每日简报</b></a>：四个栏目，每期约 9–12 条要闻加若干简讯，页首是「今日三件事」。</li>
      <li><a href="/ai/"><b>AI 前沿情报日报</b></a>：只看 AI，更细；事实与推断分开写，传闻单列为「早期信号」。综合简报的 AI 栏从这里精选。</li>
    </ul>
    <ul class="doc-secs">{secs}</ul>
    <p class="doc-note">工作日更新。某个栏目当天没有够格的内容，就写「今日从缺」，不凑数。</p>
  </section>

  <section class="doc-card"><h2>怎么选稿</h2>
    <p>每条候选消息按四个维度各打 0–2 分：</p>
    <ol class="doc-score">
      <li><b>影响面</b>会改变多少人、多少钱、多少决策</li>
      <li><b>新颖度</b>是真正的「首次」，还是小幅改进</li>
      <li><b>证据强度</b>一手材料、同行评审、人体研究优先于媒体报道，媒体报道优先于传闻；动物研究弱于人体研究</li>
      <li><b>相关度</b>与四个栏目的关联程度</li>
    </ol>
    <p>总分 6 分及以上做要闻，4–5 分进简讯，低于 4 分不收。另外几条硬规则：</p>
    <ul>
      <li>传闻只进简讯，并标明「推断/传闻」；同一条传闻一周内只报一次，除非出现新证据。</li>
      <li>连续报道的事件，只有实质新进展才再报，并附一行「前情」。同一事件只出现在一个栏目。</li>
      <li>科学栏不照期刊目录挑稿，纯理论或小众方法学最多一条要闻。</li>
      <li>抗衰栏人体研究优先（随机对照试验 &gt; 队列研究 &gt; 横断面研究），纯动物或细胞研究最多一条要闻，每条都标明研究对象；个案和无对照的商业研究不收。</li>
    </ul>
  </section>

  <section class="doc-card"><h2>标签是什么意思</h2>
    <p>每条消息带 1–2 个标签，告诉你这条信息的证据从哪里来、有多可靠。两份日报用同一套标签。</p>
    <div class="doc-tbl"><table class="doc-tags"><thead><tr><th scope="col">类别</th><th scope="col">标签</th><th scope="col">含义</th></tr></thead>
    <tbody>{"".join(rows)}</tbody></table></div>
  </section>

  <section class="doc-card"><h2>信源与付费墙</h2>
    <ul>
      <li>链接尽量指向首发或权威原站：官方公告、论文、期刊页面、原创报道。转载镜像不用，聚合网站只当线索。</li>
      <li>新闻类要闻尽量找两个以上独立来源；只有一个来源时会标「单一来源」。</li>
      <li>原文付费、我们只读到摘要或转述时，标「付费报道·二手转述」，来源名里注明「付费」或「转述」；不转载、不复述付费原文。</li>
      <li>综合简报与 AI 日报对同一件事的数字（如参数量、日期）不一致时，在当期「更正」里说明。</li>
    </ul>
  </section>

  <section class="doc-card"><h2>我们怎么做</h2>
    <p>检索、整理和初稿撰写由 AI 工具协助完成；选稿标准、写作规范、标签体系和发布前自检规则由人制定，并通过校验程序在每期发布前强制执行（如长度上限、来源必填、禁止裸链接、抗衰条目必须标研究对象）。AI 工具会出错，所以每条消息都附原始来源链接，方便你自己核对。</p>
  </section>

  <section class="doc-card"><h2>更正</h2>
    <p>发现事实错误，会在之后一期的「更正」框里写明：原期日期、哪里错了、正确的是什么，并附来源。所有已发布的更正汇总在 <a href="/corrections.html">更正记录</a>，由程序从各期数据自动生成。已发布的旧页面不做静默修改。</p>
  </section>

  <section class="doc-card"><h2>版权与免责声明</h2>
    <ul>
      <li>摘要和点评为本站原创编写；链接指向原始来源，相关内容的权利归原作者和出版方所有。</li>
      <li>不转载付费内容，也不大段引用原文。</li>
      <li>内容仅供阅读参考，不构成投资建议。<b>抗衰老与长寿栏目介绍的是研究进展，不构成医疗建议</b>；任何用药、补剂或治疗决定请咨询医生。</li>
    </ul>
  </section>

{subscribe_html("card")}"""
    return page_shell("关于 · 每日简报", "每日简报是什么、怎么选稿、标签含义、信源与更正政策。", body, "about")


# ------------------------------------------------------------- corrections
def _from_data(seen: set) -> list[dict]:
    out = []
    for f in sorted(DATA_DIR.glob("*.json")) if DATA_DIR.is_dir() else []:
        if not DATE_RE.fullmatch(f.stem):
            continue
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        cs = data.get("corrections") or []
        if cs:
            seen.add(f.stem)
        for i, c in enumerate(cs):
            src = c.get("source") or {}
            out.append({"d": f.stem, "kind": "简报", "text": c.get("text", ""), "href": f"/{f.stem[:4]}/{f.stem}.html#corr-{i + 1}",
                        "src_name": src.get("name", ""), "src_url": src.get("url", "")})
    return out


def _from_pages(site: Path, seen: set) -> list[dict]:
    out = []
    for p in sorted(site.glob("[0-9][0-9][0-9][0-9]/*.html")):
        if not DATE_RE.fullmatch(p.stem) or p.stem in seen:
            continue
        raw = p.read_text(encoding="utf-8", errors="ignore")
        for i, m in enumerate(re.finditer(r'<aside class="corr"[^>]*>(.*?)</aside>', raw, re.S)):
            inner = re.sub(r"<b>更正</b>", "", m.group(1), count=1)
            a = re.search(r'<a href="([^"]+)">(.*?)</a>', inner, re.S)
            text = re.sub(r"（<a .*?</a>）", "", inner, flags=re.S)
            text = html.unescape(re.sub(r"<[^>]+>", "", text)).strip()
            out.append({"d": p.stem, "kind": "简报", "text": text, "href": f"/{p.stem[:4]}/{p.stem}.html",
                        "src_name": html.unescape(re.sub(r"<[^>]+>", "", a.group(2))) if a else "",
                        "src_url": html.unescape(a.group(1)) if a else ""})
    return out


def _from_ai_reports(site: Path) -> list[dict]:
    out = []
    for f in sorted(AI_REPORTS.glob("*.md")) if AI_REPORTS.is_dir() else []:
        if not DATE_RE.fullmatch(f.stem) or not (site / "ai" / f"{f.stem}.html").exists():
            continue
        sec = re.search(r"^#+\s*更新与纠错\s*$(.*?)(?=^#+\s|\Z)", f.read_text(encoding="utf-8"), re.M | re.S)
        if not sec:
            continue
        for line in sec.group(1).splitlines():
            m = re.match(r"\s*[-*]\s*(?:更正[：:]|【更正】)\s*(.+)", line)
            if not m:
                continue
            text = m.group(1).strip()
            um = re.search(r"(?:([^\s：:，。]+)[：:]\s*)?(https?://\S+?)[\s。）)]*$", text)
            name, url = (um.group(1) or "来源", um.group(2)) if um else ("", "")
            if um:
                text = text[: um.start()].rstrip(" ：:，。") + "。"
            out.append({"d": f.stem, "kind": "AI 日报", "text": text, "href": f"/ai/{f.stem}.html",
                        "src_name": name, "src_url": url})
    return out


def collect_corrections(site: Path) -> list[dict]:
    seen: set = set()
    items = _from_data(seen) + _from_pages(site, seen) + _from_ai_reports(site)
    return sorted(items, key=lambda c: (c["d"], c["kind"]), reverse=True)


def corrections_html(site: Path) -> str:
    items = collect_corrections(site)
    rows = []
    for c in items:
        d = date.fromisoformat(c["d"])
        src = (f'<span class="cr-src">来源：<a href="{E(c["src_url"])}">{E(c["src_name"])}</a></span>'
               if c["src_url"] else "")
        rows.append(f'<li class="cr"><div class="cr-d"><b>{d.month:02d}.{d.day:02d}</b><small>{d.year}</small></div>'
                    f'<div class="cr-b"><p>{E(c["text"])}</p><p class="cr-m"><a href="{E(c["href"])}">'
                    f'刊于 {date_cn(d)} {E(c["kind"])}</a>{src}</p></div></li>')
    listing = (f'<ol class="cr-list">{"".join(rows)}</ol>' if rows
               else '<p class="hm-empty">目前还没有发布过更正。</p>')
    body = f"""  <header class="hm-arch-head doc-head"><p class="hm-eyebrow">透明度</p><h1>更正记录</h1>
    <p class="lede">我们在日报里发布过的全部更正，按日期倒序。目前共 {len(items)} 条。</p></header>
  <section class="doc-card cr-card">
{listing}
  </section>
  <section class="doc-card doc-small"><h2>说明</h2>
    <ul>
      <li>每条更正都写明原期日期、哪里错了、正确的是什么，并附来源。发现错误后在下一期刊出，旧页面不做静默修改。</li>
      <li>本页由程序从各期数据自动生成，每次发布时更新。</li>
      <li>AI 日报每期的「更新与纠错」小节主要记录已报道事件的后续进展，不是更正；其中明确标为「更正」的条目会收进本页。</li>
    </ul>
  </section>"""
    return page_shell("更正记录 · 每日简报", "每日简报与 AI 日报已发布的全部更正，按日期倒序。", body, "corr")


def main(site: Path) -> None:
    for name, text in (("about.html", about_html()), ("corrections.html", corrections_html(site))):
        p = site / name
        if not p.exists() or _strip_meta(p.read_text(encoding="utf-8")) != _strip_meta(text):
            p.write_text(text, encoding="utf-8")
            print(f"wrote {name}")


def _strip_meta(t: str) -> str:
    return re.sub(r"[ \t]*<!-- site-meta:start -->.*?<!-- site-meta:end -->[ \t]*\n?", "", t, flags=re.S)
