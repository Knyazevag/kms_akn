#!/usr/bin/env python3
"""
RAG KMS: Полное руководство пользователя
PDF Generation Script — версия 5.1
Автор: Александр Князев, начальник отдела технологий декарбонизации АО «НИИ НПО «ЛУЧ» — ПФ
"""

import os
from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm, cm
from reportlab.lib.colors import HexColor, white, black
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle,
    HRFlowable, KeepTogether
)
from reportlab.platypus.flowables import Flowable
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfgen import canvas as pdfcanvas

# ─── FONT SETUP ───────────────────────────────────────────────────────────────

FONT_DIR = Path("/tmp/fonts")
FONT_DIR.mkdir(exist_ok=True)

# Register Inter (covers Cyrillic). Fallback to NotoSans if Inter.ttf is absent.
_INTER_TTF = FONT_DIR / "Inter.ttf"
pdfmetrics.registerFont(TTFont(
    "Inter",
    str(_INTER_TTF) if _INTER_TTF.is_file()
    else "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf"
))

# Register NotoSans family (also covers Cyrillic, with bold/italic variants)
pdfmetrics.registerFont(TTFont("NotoSans", "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf"))
pdfmetrics.registerFont(TTFont("NotoSans-Bold", "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf"))
pdfmetrics.registerFont(TTFont("NotoSans-Italic", "/usr/share/fonts/truetype/noto/NotoSans-Italic.ttf"))
pdfmetrics.registerFont(TTFont("NotoSans-BoldItalic", "/usr/share/fonts/truetype/noto/NotoSans-BoldItalic.ttf"))
_NOTO_SEMIBOLD = "/usr/share/fonts/truetype/noto/NotoSans-SemiBold.ttf"
pdfmetrics.registerFont(TTFont(
    "NotoSans-SemiBold",
    _NOTO_SEMIBOLD if Path(_NOTO_SEMIBOLD).is_file()
    else "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf"
))
pdfmetrics.registerFontFamily(
    "NotoSans",
    normal="NotoSans",
    bold="NotoSans-Bold",
    italic="NotoSans-Italic",
    boldItalic="NotoSans-BoldItalic"
)

# Register DejaVu Sans Mono for code blocks
pdfmetrics.registerFont(TTFont("DejaVuSansMono", "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"))
pdfmetrics.registerFont(TTFont("DejaVuSansMono-Bold", "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"))
pdfmetrics.registerFont(TTFont("DejaVuSansMono-Oblique", "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Oblique.ttf"))
pdfmetrics.registerFontFamily(
    "DejaVuSansMono",
    normal="DejaVuSansMono",
    bold="DejaVuSansMono-Bold",
    italic="DejaVuSansMono-Oblique",
)

# ─── COLOR PALETTE ─────────────────────────────────────────────────────────────
C_DARK_GREEN = HexColor("#1a4a2e")      # headings
C_AMBER = HexColor("#f5a623")           # dividers, accents
C_WHITE = HexColor("#ffffff")           # background
C_TEXT = HexColor("#1a1a1a")           # body text
C_TEXT_MUTED = HexColor("#555555")     # secondary text
C_CODE_BG = HexColor("#f0f4f8")        # code block background
C_CODE_BORDER = HexColor("#c5d5e8")    # code block border
C_WARN_BG = HexColor("#fff3cd")        # "Важно" bg
C_WARN_BORDER = HexColor("#f5a623")    # "Важно" border
C_TIP_BG = HexColor("#d4edda")         # "Совет" bg
C_TIP_BORDER = HexColor("#28a745")     # "Совет" border
C_DANGER_BG = HexColor("#f8d7da")      # "Предупреждение" bg
C_DANGER_BORDER = HexColor("#dc3545")  # "Предупреждение" border
C_OUTPUT_BG = HexColor("#f8f8f8")      # terminal output bg
C_SECTION_LINE = HexColor("#e8e8e8")   # subtle separator

# ─── PAGE DIMENSIONS ───────────────────────────────────────────────────────────
PAGE_W, PAGE_H = A4
MARGIN_LEFT = 2.0 * cm
MARGIN_RIGHT = 2.0 * cm
MARGIN_TOP = 2.5 * cm
MARGIN_BOTTOM = 2.0 * cm
USABLE_W = PAGE_W - MARGIN_LEFT - MARGIN_RIGHT

# ─── STYLES ────────────────────────────────────────────────────────────────────

def make_styles():
    styles = {}

    styles["body"] = ParagraphStyle(
        "body",
        fontName="NotoSans",
        fontSize=10,
        leading=15,
        textColor=C_TEXT,
        spaceAfter=6,
        spaceBefore=0,
    )

    styles["body_bold"] = ParagraphStyle(
        "body_bold",
        parent=styles["body"],
        fontName="NotoSans-Bold",
    )

    styles["body_italic"] = ParagraphStyle(
        "body_italic",
        parent=styles["body"],
        fontName="NotoSans-Italic",
        textColor=C_TEXT_MUTED,
    )

    styles["h1"] = ParagraphStyle(
        "h1",
        fontName="NotoSans-Bold",
        fontSize=18,
        leading=24,
        textColor=C_DARK_GREEN,
        spaceBefore=20,
        spaceAfter=10,
    )

    styles["h2"] = ParagraphStyle(
        "h2",
        fontName="NotoSans-Bold",
        fontSize=14,
        leading=20,
        textColor=C_DARK_GREEN,
        spaceBefore=16,
        spaceAfter=8,
    )

    styles["h3"] = ParagraphStyle(
        "h3",
        fontName="NotoSans-SemiBold",
        fontSize=11.5,
        leading=17,
        textColor=C_DARK_GREEN,
        spaceBefore=12,
        spaceAfter=6,
    )

    styles["h4"] = ParagraphStyle(
        "h4",
        fontName="NotoSans-Bold",
        fontSize=10,
        leading=15,
        textColor=C_DARK_GREEN,
        spaceBefore=8,
        spaceAfter=4,
    )

    styles["code"] = ParagraphStyle(
        "code",
        fontName="DejaVuSansMono",
        fontSize=8.5,
        leading=13,
        textColor=HexColor("#1a1a1a"),
        leftIndent=8,
        rightIndent=8,
        spaceAfter=0,
        spaceBefore=0,
    )

    styles["output_text"] = ParagraphStyle(
        "output_text",
        fontName="DejaVuSansMono-Oblique",
        fontSize=8,
        leading=12,
        textColor=HexColor("#444444"),
        leftIndent=8,
        rightIndent=8,
        spaceAfter=0,
        spaceBefore=0,
    )

    styles["note_body"] = ParagraphStyle(
        "note_body",
        fontName="NotoSans",
        fontSize=9.5,
        leading=14,
        textColor=C_TEXT,
        leftIndent=6,
        rightIndent=6,
    )

    styles["note_title"] = ParagraphStyle(
        "note_title",
        fontName="NotoSans-Bold",
        fontSize=9.5,
        leading=14,
        textColor=C_TEXT,
        leftIndent=6,
        rightIndent=6,
        spaceAfter=3,
    )

    styles["bullet"] = ParagraphStyle(
        "bullet",
        fontName="NotoSans",
        fontSize=10,
        leading=15,
        textColor=C_TEXT,
        leftIndent=16,
        firstLineIndent=-8,
        spaceAfter=3,
    )

    styles["bullet2"] = ParagraphStyle(
        "bullet2",
        fontName="NotoSans",
        fontSize=9.5,
        leading=14,
        textColor=C_TEXT,
        leftIndent=28,
        firstLineIndent=-8,
        spaceAfter=2,
    )

    styles["table_header"] = ParagraphStyle(
        "table_header",
        fontName="NotoSans-Bold",
        fontSize=9,
        leading=13,
        textColor=C_WHITE,
    )

    styles["table_cell"] = ParagraphStyle(
        "table_cell",
        fontName="NotoSans",
        fontSize=8.5,
        leading=12,
        textColor=C_TEXT,
    )

    styles["table_cell_code"] = ParagraphStyle(
        "table_cell_code",
        fontName="DejaVuSansMono",
        fontSize=7.5,
        leading=11,
        textColor=C_TEXT,
    )

    styles["section_intro"] = ParagraphStyle(
        "section_intro",
        fontName="NotoSans-Italic",
        fontSize=10,
        leading=15,
        textColor=C_TEXT_MUTED,
        spaceAfter=10,
        spaceBefore=4,
    )

    styles["cover_title"] = ParagraphStyle(
        "cover_title",
        fontName="NotoSans-Bold",
        fontSize=42,
        leading=52,
        textColor=C_DARK_GREEN,
        alignment=TA_CENTER,
    )

    styles["cover_subtitle"] = ParagraphStyle(
        "cover_subtitle",
        fontName="NotoSans",
        fontSize=18,
        leading=26,
        textColor=C_TEXT_MUTED,
        alignment=TA_CENTER,
    )

    styles["cover_sub2"] = ParagraphStyle(
        "cover_sub2",
        fontName="NotoSans-Italic",
        fontSize=14,
        leading=20,
        textColor=C_TEXT_MUTED,
        alignment=TA_CENTER,
    )

    styles["cover_meta"] = ParagraphStyle(
        "cover_meta",
        fontName="NotoSans",
        fontSize=10,
        leading=16,
        textColor=C_TEXT_MUTED,
        alignment=TA_CENTER,
    )

    styles["ascii_diagram"] = ParagraphStyle(
        "ascii_diagram",
        fontName="DejaVuSansMono",
        fontSize=8,
        leading=12,
        textColor=HexColor("#1a4a2e"),
        leftIndent=4,
        spaceAfter=0,
        spaceBefore=0,
    )

    return styles


# ─── CUSTOM FLOWABLES ──────────────────────────────────────────────────────────

class ColoredBox(Flowable):
    """A colored box with optional left border stripe."""
    def __init__(self, content_paragraphs, bg_color, border_color, title=None, width=None):
        super().__init__()
        self.content_paragraphs = content_paragraphs
        self.bg_color = bg_color
        self.border_color = border_color
        self.title = title
        self._width = width or USABLE_W
        self.padding = 8
        self.border_width = 3

    def wrap(self, availWidth, availHeight):
        self._width = availWidth
        total_h = self.padding * 2
        inner_w = self._width - self.border_width - self.padding * 2
        for p in self.content_paragraphs:
            w, h = p.wrap(inner_w, availHeight)
            total_h += h + 3
        self._height = total_h
        return self._width, self._height

    def draw(self):
        c = self.canv
        w = self._width
        h = self._height
        c.setFillColor(self.bg_color)
        c.setStrokeColor(self.border_color)
        c.setLineWidth(0.5)
        c.roundRect(0, 0, w, h, 4, fill=1, stroke=1)
        c.setFillColor(self.border_color)
        c.rect(0, 0, self.border_width, h, fill=1, stroke=0)
        inner_w = w - self.border_width - self.padding * 2
        y = h - self.padding
        for p in self.content_paragraphs:
            pw, ph = p.wrap(inner_w, h)
            y -= ph
            p.drawOn(c, self.border_width + self.padding, y)
            y -= 3
        c.setFillColor(black)


class CodeBlock(Flowable):
    """Code block with colored background and border."""
    def __init__(self, lines, bg_color=C_CODE_BG, border_color=C_CODE_BORDER, style=None, width=None):
        super().__init__()
        self.lines = lines if isinstance(lines, list) else lines.split('\n')
        self.bg_color = bg_color
        self.border_color = border_color
        self.style = style
        self._width = width or USABLE_W
        self.padding = 8
        self.font_name = "DejaVuSansMono"
        self.font_size = 8.5
        self.line_height = 13

    def wrap(self, availWidth, availHeight):
        self._width = availWidth
        self._height = len(self.lines) * self.line_height + self.padding * 2
        return self._width, self._height

    def draw(self):
        c = self.canv
        w = self._width
        h = self._height
        c.setFillColor(self.bg_color)
        c.setStrokeColor(self.border_color)
        c.setLineWidth(0.8)
        c.roundRect(0, 0, w, h, 4, fill=1, stroke=1)
        c.setFont(self.font_name, self.font_size)
        c.setFillColor(HexColor("#1a1a1a"))
        y = h - self.padding - self.font_size
        for line in self.lines:
            display = line
            c.drawString(self.padding, y, display)
            y -= self.line_height
        c.setFillColor(black)


class OutputBlock(Flowable):
    """Terminal output block - lighter style, italic."""
    def __init__(self, lines, width=None):
        super().__init__()
        self.lines = lines if isinstance(lines, list) else lines.split('\n')
        self._width = width or USABLE_W
        self.padding = 7
        self.font_name = "DejaVuSansMono-Oblique"
        self.font_size = 8
        self.line_height = 12

    def wrap(self, availWidth, availHeight):
        self._width = availWidth
        self._height = len(self.lines) * self.line_height + self.padding * 2
        return self._width, self._height

    def draw(self):
        c = self.canv
        w = self._width
        h = self._height
        c.setFillColor(C_OUTPUT_BG)
        c.setStrokeColor(HexColor("#e0e0e0"))
        c.setLineWidth(0.5)
        c.roundRect(0, 0, w, h, 3, fill=1, stroke=1)
        c.setFont(self.font_name, self.font_size)
        c.setFillColor(HexColor("#444444"))
        y = h - self.padding - self.font_size
        for line in self.lines:
            c.drawString(self.padding, y, line)
            y -= self.line_height
        c.setFillColor(black)


class AmberDivider(Flowable):
    """Amber divider line."""
    def __init__(self, width=None, height=2, color=C_AMBER):
        super().__init__()
        self._width = width or USABLE_W
        self._height = height
        self.color = color

    def wrap(self, availWidth, availHeight):
        return self._width, self._height

    def draw(self):
        c = self.canv
        c.setFillColor(self.color)
        c.rect(0, 0, self._width, self._height, fill=1, stroke=0)
        c.setFillColor(black)


# ─── HELPER FUNCTIONS ──────────────────────────────────────────────────────────

def B(text, styles):
    """Bold paragraph."""
    return Paragraph(f"<b>{text}</b>", styles["body"])

def P(text, styles, style="body"):
    """Normal paragraph."""
    return Paragraph(text, styles[style])

def H1(text, styles):
    return Paragraph(text, styles["h1"])

def H2(text, styles):
    return Paragraph(text, styles["h2"])

def H3(text, styles):
    return Paragraph(text, styles["h3"])

def H4(text, styles):
    return Paragraph(text, styles["h4"])

def Bul(text, styles, level=1):
    """Bullet point."""
    style = "bullet" if level == 1 else "bullet2"
    bullet = "-" if level == 1 else "o"
    return Paragraph(f"{bullet}  {text}", styles[style])

def SP(h=6):
    return Spacer(1, h)

def code_block(lines, styles):
    """Code block flowable."""
    if isinstance(lines, str):
        line_list = lines.split('\n')
    else:
        line_list = lines
    return KeepTogether([CodeBlock(line_list), SP(8)])

def output_block(lines, styles):
    """Terminal output flowable."""
    if isinstance(lines, str):
        line_list = lines.split('\n')
    else:
        line_list = lines
    return KeepTogether([OutputBlock(line_list), SP(8)])

def note_box(title, content, kind="warn", styles=None):
    """Colored note box. kind: warn, tip, danger"""
    if kind == "warn":
        bg, border = C_WARN_BG, C_WARN_BORDER
        icon = "[!] Важно"
    elif kind == "tip":
        bg, border = C_TIP_BG, C_TIP_BORDER
        icon = "[i] Совет"
    elif kind == "danger":
        bg, border = C_DANGER_BG, C_DANGER_BORDER
        icon = "[X] Предупреждение"
    else:
        bg, border = C_WARN_BG, C_WARN_BORDER
        icon = title

    color_map = {"warn": "#7a5200", "tip": "#155724", "danger": "#721c24"}
    text_color = color_map.get(kind, "#000000")

    title_style = ParagraphStyle(
        "nb_title",
        fontName="NotoSans-Bold",
        fontSize=9.5,
        leading=14,
        textColor=HexColor(text_color),
        leftIndent=0,
    )
    body_style = ParagraphStyle(
        "nb_body",
        fontName="NotoSans",
        fontSize=9.5,
        leading=14,
        textColor=HexColor(text_color),
        leftIndent=0,
        spaceAfter=2,
    )

    paras = [Paragraph(f"<b>{icon}</b>", title_style)]
    if isinstance(content, str):
        paras.append(Paragraph(content, body_style))
    else:
        for item in content:
            paras.append(Paragraph(item, body_style))

    return KeepTogether([ColoredBox(paras, bg, border), SP(8)])

def what_happens_box(content, styles):
    """'Что должно произойти' box."""
    body_style = ParagraphStyle(
        "wh_body",
        fontName="NotoSans-Italic",
        fontSize=9.5,
        leading=14,
        textColor=HexColor("#0d3b5e"),
        leftIndent=0,
    )
    title_style = ParagraphStyle(
        "wh_title",
        fontName="NotoSans-Bold",
        fontSize=9.5,
        leading=14,
        textColor=HexColor("#0d3b5e"),
        leftIndent=0,
        spaceAfter=2,
    )
    paras = [Paragraph("<b>[>>] Что должно произойти</b>", title_style)]
    if isinstance(content, str):
        paras.append(Paragraph(content, body_style))
    else:
        for item in content:
            paras.append(Paragraph(item, body_style))

    return KeepTogether([
        ColoredBox(paras, HexColor("#e8f4fd"), HexColor("#1e88e5")),
        SP(8)
    ])


# ─── HEADER / FOOTER ──────────────────────────────────────────────────────────

def on_first_page(canvas, doc):
    """Cover page — no header/footer."""
    canvas.setTitle("RAG KMS: Полное руководство пользователя")
    canvas.setAuthor("Александр Князев, начальник отдела технологий декарбонизации АО «НИИ НПО «ЛУЧ» — ПФ")

def on_later_pages(canvas, doc):
    """Header and footer for all pages after cover."""
    canvas.saveState()
    page_num = doc.page

    # Header background strip
    canvas.setFillColor(C_DARK_GREEN)
    canvas.rect(0, PAGE_H - 20*mm, PAGE_W, 12*mm, fill=1, stroke=0)

    # Header text
    canvas.setFont("NotoSans", 8)
    canvas.setFillColor(C_WHITE)
    canvas.drawString(MARGIN_LEFT, PAGE_H - 13*mm, "RAG KMS: Полное руководство пользователя v5.1")

    # Page number on right
    canvas.drawRightString(PAGE_W - MARGIN_RIGHT, PAGE_H - 13*mm, f"Стр. {page_num}")

    # Amber accent line under header
    canvas.setFillColor(C_AMBER)
    canvas.rect(0, PAGE_H - 20*mm, PAGE_W, 1.5*mm, fill=1, stroke=0)

    # Footer
    canvas.setFillColor(HexColor("#e8e8e8"))
    canvas.rect(0, 10*mm, PAGE_W, 0.5*mm, fill=1, stroke=0)

    canvas.setFont("NotoSans", 7.5)
    canvas.setFillColor(C_TEXT_MUTED)
    canvas.drawString(MARGIN_LEFT, 6*mm, "© 2026 Александр Князев, АО «НИИ НПО «ЛУЧ» - ПФ. Версия 5.1.")
    canvas.drawRightString(PAGE_W - MARGIN_RIGHT, 6*mm, "obsidian.md  |  ollama.com  |  claude.ai")

    canvas.restoreState()


# ─── DOCUMENT BUILDER ─────────────────────────────────────────────────────────

def build_document():
    output_path = os.path.expanduser("~/KMS/rag_final_guide.pdf")
    styles = make_styles()
    story = []

    # ═══════════════════════════════════════════════════════════════════════════
    # COVER PAGE
    # ═══════════════════════════════════════════════════════════════════════════

    story.append(SP(60))
    story.append(AmberDivider(height=4, color=C_AMBER))
    story.append(SP(30))
    story.append(Paragraph("RAG KMS", styles["cover_title"]))
    story.append(SP(12))
    story.append(AmberDivider(height=2, color=C_AMBER))
    story.append(SP(12))
    story.append(Paragraph("Полное руководство пользователя", styles["cover_subtitle"]))
    story.append(SP(16))
    story.append(Paragraph(
        "Интеллектуальная система поиска по документам — версия 5.1",
        styles["cover_sub2"]
    ))
    story.append(SP(60))
    story.append(AmberDivider(height=1, color=HexColor("#cccccc")))
    story.append(SP(20))

    story.append(Paragraph(
        "<b>Версия 5.1  •  2026</b>",
        ParagraphStyle("cover_info", fontName="NotoSans-Bold", fontSize=12,
                       leading=20, textColor=C_DARK_GREEN, alignment=TA_CENTER)
    ))
    story.append(SP(8))
    story.append(Paragraph(
        "Автор: Александр Князев,",
        ParagraphStyle("cover_author", fontName="NotoSans", fontSize=11,
                       leading=18, textColor=C_TEXT_MUTED, alignment=TA_CENTER)
    ))
    story.append(SP(4))
    story.append(Paragraph(
        "начальник отдела технологий декарбонизации АО «НИИ НПО «ЛУЧ» — ПФ",
        ParagraphStyle("cover_author2", fontName="NotoSans", fontSize=11,
                       leading=18, textColor=C_TEXT_MUTED, alignment=TA_CENTER)
    ))
    story.append(SP(16))
    story.append(Paragraph(
        "Ubuntu · Python · Ollama · ChromaDB · Obsidian · Claude Code · MCP",
        ParagraphStyle("cover_tech", fontName="NotoSans", fontSize=9.5,
                       leading=14, textColor=C_TEXT_MUTED, alignment=TA_CENTER)
    ))
    story.append(SP(16))
    story.append(Paragraph(
        "PDF, DOCX, DOC, TXT, MD, XLSX, CSV, PPTX, ODT",
        ParagraphStyle("cover_tech2", fontName="NotoSans", fontSize=9,
                       leading=14, textColor=C_TEXT_MUTED, alignment=TA_CENTER)
    ))
    story.append(SP(80))
    story.append(AmberDivider(height=4, color=C_DARK_GREEN))
    story.append(PageBreak())

    # ════════════════════════════════════════════════════════════════════════
    # ОСНОВНОЙ ТЕКСТ — рендерится напрямую из rag_final_guide.md
    # (Содержание, все разделы, приложения, шпаргалка). Это гарантирует, что
    # PDF всегда совпадает с текстом руководства.
    # ════════════════════════════════════════════════════════════════════════
    _render_markdown_body(story, styles)

    # ════════════════════════════════════════════════════════════════════════
    # ФИНАЛ
    # ════════════════════════════════════════════════════════════════════════
    story.append(SP(16))
    story.append(AmberDivider(height=3))
    story.append(SP(12))
    story.append(Paragraph(
        "<b>Успехов в работе с системой управления знаниями!</b>",
        ParagraphStyle("final", fontName="NotoSans-Bold", fontSize=12,
                       leading=18, textColor=C_DARK_GREEN, alignment=TA_CENTER)
    ))
    story.append(SP(4))
    story.append(Paragraph(
        "Александр Князев, начальник отдела технологий декарбонизации АО «НИИ НПО «ЛУЧ» — ПФ",
        ParagraphStyle("final2", fontName="NotoSans-Italic", fontSize=9.5,
                       leading=14, textColor=C_TEXT_MUTED, alignment=TA_CENTER)
    ))
    story.append(SP(12))
    story.append(AmberDivider(height=1, color=HexColor("#cccccc")))

    # ─── BUILD ──────────────────────────────────────────────────────────────
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        title="RAG KMS: Полное руководство пользователя",
        author="Александр Князев, начальник отдела технологий декарбонизации АО «НИИ НПО «ЛУЧ» — ПФ",
        leftMargin=MARGIN_LEFT,
        rightMargin=MARGIN_RIGHT,
        topMargin=MARGIN_TOP,
        bottomMargin=MARGIN_BOTTOM,
    )
    doc.build(story, onFirstPage=on_first_page, onLaterPages=on_later_pages)
    print(f"PDF created: {output_path}")
    return output_path


# ════════════════════════════════════════════════════════════════════════════
# MARKDOWN → branded flowables
# Преобразует rag_final_guide.md в набор флоуэблов с фирменным оформлением:
# заголовки, абзацы, списки, таблицы, блоки кода/вывода и цветные плашки
# ([i] Совет / [!] Важно / [>>] Что увидите / ✓ Это нормально).
# ════════════════════════════════════════════════════════════════════════════
import re as _re

_CODE_WRAP = 90   # макс. символов в строке кода (DejaVuSansMono 8.5pt)
_OUT_WRAP = 95    # макс. символов в строке вывода (8pt)
_DIAGRAM_CHARS = "│─┌┐└┘├┤┬┴┼╔╗╚╝║═▼▲◄►╰╯╭╮"


def _esc(s):
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _inline(children):
    out = []
    for t in children or []:
        ty = t.get("type")
        if ty == "text":
            out.append(_esc(t.get("raw", "")))
        elif ty == "strong":
            out.append("<b>" + _inline(t.get("children")) + "</b>")
        elif ty == "emphasis":
            out.append("<i>" + _inline(t.get("children")) + "</i>")
        elif ty == "codespan":
            out.append('<font face="DejaVuSansMono" size="9">' + _esc(t.get("raw", "")) + "</font>")
        elif ty == "link":
            url = (t.get("attrs") or {}).get("url", "") or ""
            inner = _inline(t.get("children"))
            if "://" in url or url.startswith("mailto:"):
                out.append('<a href="%s" color="#1a4a2e">%s</a>' % (_esc(url), inner))
            else:
                # внутренние якоря (#...) reportlab не умеет — оставляем текст
                out.append(inner)
        elif ty == "linebreak":
            out.append("<br/>")
        elif ty == "softbreak":
            out.append(" ")
        elif ty == "image":
            out.append(_esc((t.get("attrs") or {}).get("alt", "")))
        elif "children" in t:
            out.append(_inline(t.get("children")))
        elif "raw" in t:
            out.append(_esc(t.get("raw", "")))
    return "".join(out)


def _plain(children):
    out = []
    for t in children or []:
        if t.get("type") == "text":
            out.append(t.get("raw", ""))
        elif "children" in t:
            out.append(_plain(t.get("children")))
        elif "raw" in t:
            out.append(t.get("raw", ""))
    return "".join(out)


def _wrap_lines(lines, maxch):
    out = []
    for ln in lines:
        if len(ln) <= maxch:
            out.append(ln)
            continue
        s = ln
        while len(s) > maxch:
            cut = s.rfind(" ", 0, maxch)
            if cut < int(maxch * 0.55):
                cut = maxch
            out.append(s[:cut])
            s = "    " + s[cut:].lstrip(" ")
        out.append(s)
    return out


def _render_code(tok, story, styles):
    raw = tok.get("raw", "").rstrip("\n")
    lines = raw.split("\n")
    info = ((tok.get("attrs") or {}).get("info") or "").strip()
    lang = info.split()[0].lower() if info else ""
    is_diagram = any(ch in raw for ch in _DIAGRAM_CHARS)
    if lang or is_diagram:
        story.append(code_block(_wrap_lines(lines, _CODE_WRAP), styles))
    else:
        story.append(output_block(_wrap_lines(lines, _OUT_WRAP), styles))


_MARK_RE = _re.compile(r'^\s*(\[i\]|\[!\]|\[X\]|\[&gt;&gt;\]|✓|✗)\s*')
# Слово, которое плашка уже печатает в своей иконке ([!] Важно и т.п.).
_ICON_WORD = {"warn": "Важно", "tip": "Совет", "danger": "Предупреждение"}


def _strip_label_word(h, word):
    """Убирает дублирующее слово-метку из начала жирного заголовка плашки,
    сохраняя уточнение. Напр. '<b>Важно (о путях):</b> ...' -> '<b>(о путях):</b> ...'."""
    m = _re.match(r'^\s*<b>(.*?)</b>(.*)$', h, _re.S)
    if not m:
        return h
    inner, after = m.group(1), m.group(2)
    new_inner = _re.sub(r'^\s*' + _re.escape(word) + r'\b[\s:：]*', '', inner)
    if new_inner == inner:
        return h
    new_inner = new_inner.strip()
    if new_inner:
        return '<b>' + new_inner + '</b>' + after
    return after.lstrip()


def _strip_marker(h, kind=None):
    h = h.replace("[&gt;&gt;]", "")
    h = _MARK_RE.sub("", h)
    word = _ICON_WORD.get(kind)
    if word:
        h = _strip_label_word(h, word)
    return h.strip()


def _quote_kind(plain):
    t = plain.strip()
    if t.startswith("[>>]"):
        return "what"
    if t.startswith("[!]"):
        return "warn"
    if t.startswith("[i]"):
        return "tip"
    if t.startswith("[X]") or t.startswith("✗"):
        return "danger"
    if t.startswith("✓") or t.lower().startswith("это нормально"):
        return "tip"
    return None


def _render_quote(tok, story, styles, state):
    inner = tok.get("children", [])
    first_plain = ""
    for c in inner:
        if c.get("type") == "paragraph":
            first_plain = _plain(c.get("children")).strip()
            break
    kind = _quote_kind(first_plain)
    lead, rest = [], []
    seen_rest = False
    for c in inner:
        if (not seen_rest) and c.get("type") == "paragraph":
            lead.append(c)
        else:
            seen_rest = True
            rest.append(c)
    lead_html = []
    for i, c in enumerate(lead):
        h = _inline(c.get("children"))
        if i == 0:
            h = _strip_marker(h, kind)
        if h.strip():
            lead_html.append(h)
    if kind == "what":
        story.append(what_happens_box(lead_html or [" "], styles))
    elif kind in ("warn", "tip", "danger"):
        story.append(note_box("", lead_html or [" "], kind=kind, styles=styles))
    else:
        for h in lead_html:
            story.append(P(h, styles, "section_intro"))
    for c in rest:
        _render_block(c, story, styles, state)


def _render_list(tok, story, styles, state, level=1):
    attrs = tok.get("attrs") or {}
    ordered = attrs.get("ordered", False)
    idx = attrs.get("start", 1) or 1
    for it in tok.get("children", []):
        parts, subs, extra = [], [], []
        for c in it.get("children", []):
            ct = c.get("type")
            if ct in ("block_text", "paragraph"):
                parts.append(_inline(c.get("children")))
            elif ct == "list":
                subs.append(c)
            else:
                extra.append(c)
        joined = " ".join(p for p in parts if p)
        if ordered:
            sty = "bullet" if level == 1 else "bullet2"
            story.append(P("%d.  %s" % (idx, joined), styles, sty))
        else:
            story.append(Bul(joined, styles, level=1 if level == 1 else 2))
        for s2 in subs:
            _render_list(s2, story, styles, state, level + 1)
        for c in extra:
            _render_block(c, story, styles, state)
        idx += 1


def _render_table(tok, story, styles):
    head, rows = [], []
    for part in tok.get("children", []):
        pt = part.get("type")
        if pt == "table_head":
            head = [_inline(c.get("children")) for c in part.get("children", [])]
        elif pt == "table_body":
            for r in part.get("children", []):
                rows.append([_inline(c.get("children")) for c in r.get("children", [])])
    if not head and not rows:
        return
    ncols = len(head) or len(rows[0])
    data = []
    if head:
        data.append([Paragraph(h, styles["table_header"]) for h in head])
    for r in rows:
        r = list(r) + [""] * (ncols - len(r))
        data.append([Paragraph(c, styles["table_cell"]) for c in r[:ncols]])
    colw = [USABLE_W / ncols] * ncols
    t = Table(data, colWidths=colw, repeatRows=1 if head else 0)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), C_DARK_GREEN),
        ("TEXTCOLOR", (0, 0), (-1, 0), white),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [white, HexColor("#f0f7f0")]),
        ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#c5d5c5")),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(t)
    story.append(SP(8))


def _render_heading(tok, story, styles):
    lvl = (tok.get("attrs") or {}).get("level", 1)
    html = _inline(tok.get("children"))
    if lvl <= 2:
        story.append(H1(html, styles))
        story.append(AmberDivider(height=1, color=C_AMBER))
        story.append(SP(4))
    elif lvl == 3:
        story.append(H2(html, styles))
    elif lvl == 4:
        story.append(H3(html, styles))
    else:
        story.append(H4(html, styles))


def _render_block(tok, story, styles, state):
    ty = tok.get("type")
    if ty == "heading":
        lvl = (tok.get("attrs") or {}).get("level", 1)
        if lvl == 1 and not state["seen_title"]:
            state["seen_title"] = True
            return
        _render_heading(tok, story, styles)
    elif ty == "paragraph":
        if _plain(tok.get("children")).strip().startswith("Версия:"):
            return
        story.append(P(_inline(tok.get("children")), styles))
    elif ty == "block_code":
        _render_code(tok, story, styles)
    elif ty == "block_quote":
        _render_quote(tok, story, styles, state)
    elif ty == "list":
        _render_list(tok, story, styles, state, 1)
    elif ty == "table":
        _render_table(tok, story, styles)
    elif ty == "thematic_break":
        story.append(SP(6))
    elif ty == "blank_line":
        return
    else:
        for c in tok.get("children", []) or []:
            _render_block(c, story, styles, state)


def _render_markdown_body(story, styles):
    import mistune
    md_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rag_final_guide.md")
    text = open(md_path, encoding="utf-8").read()
    text = text.replace("✅", "✓").replace("❌", "✗")
    parser = mistune.create_markdown(renderer=None, plugins=["table"])
    state = {"seen_title": False}
    for tok in parser(text):
        _render_block(tok, story, styles, state)


if __name__ == "__main__":
    result = build_document()
    print(f"Done: {result}")
