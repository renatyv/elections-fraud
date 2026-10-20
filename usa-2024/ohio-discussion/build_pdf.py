"""Compile this packet's Markdown subset to PDF; requires reportlab."""
from pathlib import Path
import re
from xml.sax.saxutils import escape
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.utils import ImageReader
from reportlab.platypus import SimpleDocTemplate, Paragraph, Image, Spacer, PageBreak, Preformatted

ROOT = Path(__file__).resolve().parent


def inline(text: str) -> str:
    text = escape(text)
    return re.sub(r'\[([^\]]+)\]\((https?://[^)]+)\)', r'<a href="\2" color="#24668b">\1</a>', text)


def footer(canvas: object, doc: object) -> None:
    canvas.saveState()
    canvas.setFont('Helvetica', 8)
    canvas.setFillColor(colors.HexColor('#536477'))
    canvas.drawString(44, 28, 'Ohio Senate 2024 | Discussion draft | 18 October 2026')
    canvas.drawRightString(551, 28, str(doc.page))
    canvas.restoreState()


def main() -> None:
    output = ROOT/'output/pdf/ohio_senate_discussion.pdf'
    output.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(str(output), pagesize=(595.28,841.89),
        rightMargin=44,leftMargin=44,topMargin=40,bottomMargin=44,
        title='Ohio Senate 2024: a second-digit anomaly',author='Renat Yuldashev')
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='BodyReport',fontName='Helvetica',fontSize=10,leading=14,
        spaceAfter=9,textColor=colors.HexColor('#24364a'),splitLongWords=True))
    styles.add(ParagraphStyle(name='CodeReport',fontName='Courier',fontSize=9,leading=13,spaceAfter=10))
    for name in ['Title','Heading1','Heading2']:
        styles[name].textColor=colors.HexColor('#16324f')
        styles[name].alignment=TA_LEFT
    story = []
    blocks = (ROOT/'REPORT.md').read_text().split('\n\n')
    for block in blocks:
        block=block.strip()
        if not block:
            continue
        if block=='<!-- pagebreak -->':
            story.append(PageBreak())
        elif block.startswith('!['):
            match=re.fullmatch(r'!\[([^\]]*)\]\(([^)]+)\)',block)
            assert match, block
            image_path=ROOT/match[2]
            width,height=ImageReader(str(image_path)).getSize()
            story.append(Image(str(image_path),width=doc.width,height=doc.width*height/width))
            story.append(Spacer(1,8))
        elif block.startswith('```'):
            story.append(Preformatted(block.strip('`\n'),styles['CodeReport']))
        elif block.startswith('#'):
            level=len(block)-len(block.lstrip('#'))
            story.append(Paragraph(inline(block.lstrip('# ')),styles[{1:'Title',2:'Heading1',3:'Heading2'}[level]]))
        elif block.startswith('- ') or re.match(r'\d+\. ',block):
            for line in block.splitlines():
                story.append(Paragraph(inline(line),styles['BodyReport']))
        else:
            story.append(Paragraph(inline(block.replace('\n',' ')),styles['BodyReport']))
    assert len(story)>30
    doc.build(story,onFirstPage=footer,onLaterPages=footer)
    print(output)


if __name__ == '__main__':
    main()
