# -*- coding: utf-8 -*-
"""服务端 PDF 简历导出（#1）。

用 reportlab 按数据生成标准 A4 PDF，纯 Python 实现、不额外增大安装包体积。
中文字体使用 PDF 内置的 STSong-Light（CID 字体），无需携带字体文件。
"""
import html
from io import BytesIO
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.platypus import (
    HRFlowable,
    Image,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
)

pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))

_ZH_FONT = "STSong-Light"

_BASE = {
    "fontName": _ZH_FONT,
    "leading": 15,
    "spaceAfter": 4,
}
_NAME = ParagraphStyle("name", parent=getSampleStyleSheet()["Title"], fontName=_ZH_FONT,
                       fontSize=21, leading=26, alignment=TA_CENTER, textColor=colors.HexColor("#1f2937"))
_CONTACT = ParagraphStyle("contact", parent=getSampleStyleSheet()["BodyText"],
                          fontName=_ZH_FONT, fontSize=9.5, leading=14, alignment=TA_CENTER,
                          textColor=colors.HexColor("#6b7280"))
_H = ParagraphStyle("h", parent=getSampleStyleSheet()["Heading2"], fontName=_ZH_FONT,
                    fontSize=12.5, leading=17, textColor=colors.HexColor("#0f766e"),
                    spaceBefore=10, spaceAfter=3)
_BODY = ParagraphStyle("body", parent=getSampleStyleSheet()["BodyText"], **_BASE)
_ITEM = ParagraphStyle("item", parent=_BODY, fontSize=10.5, leading=15, spaceAfter=2)

# 证件照目录（与 app.py 的 PHOTO_DIR 对齐）
_PHOTO_DIR = Path(__file__).resolve().parent / "data" / "uploads" / "photos"


def _esc(text: str) -> str:
    return html.escape(str(text or ""), quote=False).replace("\n", "<br/>")


def _sec(flow, title, items):
    if not items:
        return
    flow.append(Paragraph(_esc(title), _H))
    for text in items:
        flow.append(Paragraph(_esc(text), _ITEM))


def _self_eval_items(p, L):
    tags = p.get("self_tags") or []
    eval_text = p.get("self_eval") or ""
    items = []
    if tags:
        items.append("、".join(tags))
    if eval_text:
        items.append(eval_text)
    return items


def build_resume_pdf(ctx: dict, lang: str = "zh") -> bytes:
    """按简历上下文生成 A4 PDF，返回字节。ctx 来自 app.resume_context()。"""
    p = ctx.get("profile") or {}
    L = ctx.get("L") or {}
    name = p.get("name") or L.get("name", "My Resume")
    contact = "  |  ".join(x for x in [
        p.get("phone"), p.get("email"), p.get("hometown"), p.get("address"),
    ] if x)
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=16 * mm, rightMargin=16 * mm, topMargin=14 * mm, bottomMargin=14 * mm,
        title=f"{name} - Resume", author="滴鱼简历助手 XG Resume Studio",
    )
    story = []

    photo_url = p.get("photo_path") or ""
    if photo_url:
        local = _PHOTO_DIR / Path(str(photo_url)).name
        if local.exists():
            try:
                story.append(Image(str(local), width=22 * mm, height=29 * mm))
            except Exception:
                pass

    story.append(Paragraph(_esc(name), _NAME))
    if contact:
        story.append(Paragraph(_esc(contact), _CONTACT))
    extra = "  |  ".join(x for x in [p.get("gender"), p.get("birth_date")] if x)
    if extra:
        story.append(Paragraph(_esc(extra), _CONTACT))
    story.append(Spacer(1, 4))
    story.append(HRFlowable(width="100%", thickness=1.1, color=colors.HexColor("#0f766e")))

    secs = []
    if p.get("summary"):
        secs.append(("summary", [p.get("summary")]))
    self_items = _self_eval_items(p, L)
    if self_items:
        secs.append(("self_eval", self_items))

    def _edu(e):
        line = f"{e.get('school')} | {e.get('degree')} | {e.get('major')}  ({e.get('start')} - {e.get('end')})"
        return [line] + ([e.get("notes")] if e.get("notes") else [])

    def _paper(a):
        return [a.get("citation") or ""]

    def _project(pr):
        line = f"{pr.get('name')}（{pr.get('role')}，{pr.get('start')} - {pr.get('end')}）"
        return [line] + ([pr.get("description")] if pr.get("description") else [])

    def _award(a):
        line = f"{a.get('date')}  {a.get('title')}（{a.get('level')}）"
        out = [line]
        if a.get("organizer"):
            out.append(f"{L.get('organizer', '颁奖单位：')}{a.get('organizer')}")
        return out

    def _position(po):
        line = f"{po.get('start')} - {po.get('end')}  {po.get('title')}  {po.get('org')}"
        return [line] + ([po.get("description")] if po.get("description") else [])

    builders = {
        "education": _edu, "papers": _paper, "projects": _project,
        "awards": _award, "positions": _position,
    }
    for key, fn in builders.items():
        items = []
        for r in ctx.get(key) or []:
            items.extend(fn(r))
        if items:
            secs.append((key, items))

    skill_items = []
    if p.get("skills"):
        skill_items.append("、".join(p["skills"]))
    if p.get("languages"):
        skill_items.append(f"{L.get('languages', '语言能力：')}{'、'.join(p['languages'])}")
    if skill_items:
        secs.append(("skills", skill_items))

    for key, items in secs:
        _sec(story, L.get(key, key), items)

    doc.build(story)
    return buf.getvalue()