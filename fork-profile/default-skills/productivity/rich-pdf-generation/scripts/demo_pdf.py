#!/usr/bin/env python3
"""
demo_pdf.py — Rich PDF generation demo
Tests the full pipeline: ReportLab Platypus + matplotlib charts
Run: python3 demo_pdf.py
Output: demo_output.pdf in the current directory
"""

import io
import matplotlib
matplotlib.use("Agg")   # non-interactive backend — required for PDF embed
import matplotlib.pyplot as plt
import matplotlib as mpl
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame, Paragraph,
    Spacer, Table, TableStyle, LongTable, Image, PageBreak,
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

OUTPUT = "demo_output.pdf"

# ------------------------------------------------------------------
# Colour palette
# ------------------------------------------------------------------
PALETTE = {
    "primary":   "#16213e",
    "secondary": "#0f3460",
    "accent":    "#e94560",
    "light":     "#a8dadc",
    "bg_alt":    "#f1faee",
    "text":      "#1d3557",
}

def hc(h):
    return colors.HexColor(h)

# ------------------------------------------------------------------
# Styles
# ------------------------------------------------------------------
styles = getSampleStyleSheet()
title_style = ParagraphStyle(
    "title", fontSize=24, fontName="Helvetica-Bold",
    textColor=hc(PALETTE["primary"]), spaceAfter=12, leading=30,
)
subtitle_style = ParagraphStyle(
    "subtitle", fontSize=12, fontName="Helvetica",
    textColor=hc(PALETTE["secondary"]), spaceAfter=8,
)
heading_style = ParagraphStyle(
    "h1", fontSize=14, fontName="Helvetica-Bold",
    textColor=hc(PALETTE["primary"]), spaceBefore=14, spaceAfter=6,
)
body_style = ParagraphStyle(
    "body", fontSize=10, fontName="Helvetica",
    textColor=hc(PALETTE["text"]), leading=14, spaceAfter=8,
)

# ------------------------------------------------------------------
# Page layout
# ------------------------------------------------------------------
PAGE_W, PAGE_H = A4
MARGIN = 2 * cm

def on_page(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica-Bold", 8)
    canvas.setFillColor(hc(PALETTE["primary"]))
    canvas.drawString(MARGIN, PAGE_H - 1.2 * cm, "Demo Report · Rich PDF Generation")
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(hc(PALETTE["text"]))
    canvas.drawRightString(PAGE_W - MARGIN, PAGE_H - 1.2 * cm, "Hermes · 2026")
    canvas.setStrokeColor(hc(PALETTE["light"]))
    canvas.line(MARGIN, PAGE_H - 1.4 * cm, PAGE_W - MARGIN, PAGE_H - 1.4 * cm)
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.grey)
    canvas.drawCentredString(PAGE_W / 2, 0.8 * cm, f"Page {doc.page}")
    canvas.restoreState()

frame = Frame(
    MARGIN, MARGIN + 0.5 * cm,
    PAGE_W - 2 * MARGIN, PAGE_H - 2 * MARGIN - 1.5 * cm,
    id="main",
)
page_template = PageTemplate(id="main", frames=[frame], onPage=on_page)
doc = BaseDocTemplate(OUTPUT, pagesize=A4, pageTemplates=[page_template])

# ------------------------------------------------------------------
# Chart helper
# ------------------------------------------------------------------
def chart_to_image(fig, width_cm=14, height_cm=7, dpi=150):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=dpi, bbox_inches="tight",
                facecolor=fig.get_facecolor())
    buf.seek(0)
    return Image(buf, width=width_cm * cm, height=height_cm * cm)

def make_bar_chart():
    mpl.rcParams.update({"axes.spines.top": False, "axes.spines.right": False})
    cats = ["Q1", "Q2", "Q3", "Q4"]
    series = {
        "North": [120, 145, 130, 160],
        "South": [98,  112, 105, 130],
        "East":  [200, 180, 215, 225],
    }
    bar_colors = [PALETTE["primary"], PALETTE["secondary"], PALETTE["accent"]]
    x = range(len(cats))
    n = len(series)
    width = 0.7 / n

    fig, ax = plt.subplots(figsize=(10, 5))
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")
    for i, (name, vals) in enumerate(series.items()):
        offsets = [xi + i * width for xi in x]
        ax.bar(offsets, vals, width=width, label=name,
               color=bar_colors[i % len(bar_colors)])
    ax.set_xticks([xi + width for xi in x])
    ax.set_xticklabels(cats)
    ax.set_title("Quarterly Revenue by Region", fontsize=13, fontweight="bold",
                 color=PALETTE["text"], pad=12)
    ax.legend(frameon=False)
    ax.yaxis.grid(True, linestyle="--", alpha=0.4)
    fig.tight_layout()
    return fig

def make_line_chart():
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun"]
    fig, ax = plt.subplots(figsize=(10, 4))
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")
    ax.plot(months, [80, 95, 110, 130, 125, 150],
            color=PALETTE["primary"], linewidth=2.5, marker="o", label="Revenue")
    ax.fill_between(months, [80, 95, 110, 130, 125, 150],
                    alpha=0.12, color=PALETTE["primary"])
    ax.plot(months, [60, 70, 80, 90, 85, 105],
            color=PALETTE["accent"], linewidth=2, marker="s", linestyle="--", label="Costs")
    ax.set_title("Revenue vs Costs (H1)", fontsize=13, fontweight="bold",
                 color=PALETTE["text"], pad=12)
    ax.legend(frameon=False)
    ax.yaxis.grid(True, linestyle="--", alpha=0.4)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    return fig

# ------------------------------------------------------------------
# Table builder
# ------------------------------------------------------------------
def build_table():
    data = [
        ["Region", "Q1", "Q2", "Q3", "Q4", "Total"],
        ["North",  120,   145,  130,  160,  555],
        ["South",  98,    112,  105,  130,  445],
        ["East",   200,   180,  215,  225,  820],
        ["West",   85,    95,   90,   110,  380],
        ["TOTAL",  503,   532,  540,  625,  2200],
    ]

    # Conditional colour: highlight East row (highest)
    col_w = [3.5*cm, 2*cm, 2*cm, 2*cm, 2*cm, 2.5*cm]
    table = LongTable(data, colWidths=col_w, repeatRows=1)
    base_styles = [
        ("BACKGROUND",    (0, 0),  (-1, 0),  hc(PALETTE["primary"])),
        ("TEXTCOLOR",     (0, 0),  (-1, 0),  colors.white),
        ("FONTNAME",      (0, 0),  (-1, 0),  "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0),  (-1, 0),  10),
        ("TOPPADDING",    (0, 0),  (-1, 0),  8),
        ("BOTTOMPADDING", (0, 0),  (-1, 0),  8),
        ("ROWBACKGROUNDS",(0, 1),  (-1, -2), [colors.white, hc(PALETTE["bg_alt"])]),
        ("BACKGROUND",    (0, -1), (-1, -1), hc(PALETTE["secondary"])),
        ("TEXTCOLOR",     (0, -1), (-1, -1), colors.white),
        ("FONTNAME",      (0, -1), (-1, -1), "Helvetica-Bold"),
        ("GRID",          (0, 0),  (-1, -1), 0.4, colors.lightgrey),
        ("LINEABOVE",     (0, -1), (-1, -1), 1.5, hc(PALETTE["accent"])),
        ("ALIGN",         (1, 0),  (-1, -1), "RIGHT"),
        ("ALIGN",         (0, 0),  (0, -1),  "LEFT"),
        ("LEFTPADDING",   (0, 0),  (-1, -1), 6),
        ("RIGHTPADDING",  (0, 0),  (-1, -1), 6),
        ("TOPPADDING",    (0, 1),  (-1, -1), 5),
        ("BOTTOMPADDING", (0, 1),  (-1, -1), 5),
    ]
    # Highlight East row (row index 3)
    base_styles += [
        ("BACKGROUND", (0, 3), (-1, 3), hc(PALETTE["light"])),
        ("TEXTCOLOR",  (0, 3), (-1, 3), hc(PALETTE["primary"])),
        ("FONTNAME",   (0, 3), (-1, 3), "Helvetica-Bold"),
    ]
    table.setStyle(TableStyle(base_styles))
    return table

# ------------------------------------------------------------------
# Build document
# ------------------------------------------------------------------
elements = []

# Cover page
elements.append(Spacer(1, 3 * cm))
elements.append(Paragraph("Rich PDF Generation Demo", title_style))
elements.append(Paragraph("Hermes · ReportLab + matplotlib pipeline · 2026", subtitle_style))
elements.append(Spacer(1, 1 * cm))
elements.append(Paragraph(
    "This document demonstrates the full rich-pdf-generation skill: colour-themed "
    "tables with zebra striping and conditional highlighting, embedded matplotlib "
    "charts (bar and line), multi-page layout with header/footer, and page numbers.",
    body_style,
))
elements.append(PageBreak())

# Section 1 — Table
elements.append(Paragraph("Section 1: Revenue Summary Table", heading_style))
elements.append(Paragraph(
    "The table below uses a dark navy header, alternating row backgrounds, an "
    "accent line above the summary row, and conditional highlighting for the "
    "highest-performing region (East).",
    body_style,
))
elements.append(Spacer(1, 0.3 * cm))
elements.append(build_table())
elements.append(Spacer(1, 0.8 * cm))

# Section 2 — Bar chart
elements.append(Paragraph("Section 2: Quarterly Revenue by Region", heading_style))
elements.append(Paragraph(
    "Grouped bar chart rendered via matplotlib at 150 DPI, embedded as a PNG "
    "image. Colour palette matches the table above.",
    body_style,
))
fig1 = make_bar_chart()
elements.append(chart_to_image(fig1, 14, 7))
plt.close(fig1)
elements.append(Spacer(1, 0.8 * cm))

# Section 3 — Line chart
elements.append(Paragraph("Section 3: Revenue vs Costs Trend", heading_style))
elements.append(Paragraph(
    "Area-filled line chart with two series. Area fill shows cumulative revenue "
    "volume; dashed line shows costs for visual contrast.",
    body_style,
))
fig2 = make_line_chart()
elements.append(chart_to_image(fig2, 14, 6))
plt.close(fig2)

# Build — use build() (no TOC in this demo)
doc.build(elements)
print(f"Done: {OUTPUT}")
