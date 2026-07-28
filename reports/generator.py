"""HTML and PDF report generation."""

from __future__ import annotations

import html
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

from utils.paths import REPORTS, ensure_directories


def generate_html_report(
    title: str,
    summary: Dict[str, Any],
    sections: List[Dict[str, Any]],
) -> Path:
    """Generate a self-contained HTML report and return its path."""
    ensure_directories()
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = REPORTS / f"report_{stamp}.html"

    rows = ""
    for key, val in summary.items():
        rows += f"<tr><td>{html.escape(str(key))}</td><td>{html.escape(str(val))}</td></tr>\n"

    sections_html = ""
    for sec in sections:
        sections_html += f"<h2>{html.escape(sec.get('title', ''))}</h2>\n"
        sections_html += f"<p>{html.escape(sec.get('body', ''))}</p>\n"
        if sec.get("items"):
            sections_html += "<ul>\n"
            for item in sec["items"]:
                sections_html += f"<li>{html.escape(str(item))}</li>\n"
            sections_html += "</ul>\n"

    content = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<title>{html.escape(title)}</title>
<style>
  body {{ font-family: 'Segoe UI', sans-serif; margin: 40px; background: #1c1c1e; color: #fff; }}
  h1 {{ color: #0a84ff; }}
  table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
  td, th {{ border: 1px solid #38383a; padding: 10px; text-align: left; }}
  th {{ background: #2c2c2e; }}
</style>
</head>
<body>
<h1>{html.escape(title)}</h1>
<p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
<table>
<tr><th>Metric</th><th>Value</th></tr>
{rows}
</table>
{sections_html}
</body>
</html>
"""
    path.write_text(content, encoding="utf-8")
    return path


def generate_pdf_report(
    title: str,
    summary: Dict[str, Any],
    sections: List[Dict[str, Any]],
) -> Path | None:
    """Generate a simple PDF report using reportlab if available."""
    ensure_directories()
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = REPORTS / f"report_{stamp}.pdf"
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib import colors

        doc = SimpleDocTemplate(str(path), pagesize=A4)
        styles = getSampleStyleSheet()
        story = [
            Paragraph(title, styles["Title"]),
            Spacer(1, 12),
            Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles["Normal"]),
            Spacer(1, 20),
        ]
        data = [["Metric", "Value"]] + [[str(k), str(v)] for k, v in summary.items()]
        t = Table(data, colWidths=[200, 300])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0A84FF")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ]))
        story.append(t)
        for sec in sections:
            story.append(Spacer(1, 16))
            story.append(Paragraph(sec.get("title", ""), styles["Heading2"]))
            story.append(Paragraph(sec.get("body", ""), styles["Normal"]))
        doc.build(story)
        return path
    except Exception:
        return None
