"""Export the measured Markdown report and render every page for visual QA."""
import re
from datetime import date
from html import escape
from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, PageBreak, Table, TableStyle
from pypdf import PdfReader
import pypdfium2 as pdfium

ROOT=Path(__file__).resolve().parents[1]


def markdown_table(block,styles):
    """Render a GitHub-style pipe table; the exporter previously flattened these."""
    cell=ParagraphStyle('Cell',parent=styles['ReportBody'],fontSize=8.5,leading=11,spaceAfter=0)
    head=ParagraphStyle('CellHead',parent=cell,fontName='Helvetica-Bold',textColor=colors.HexColor('#315c9c'))
    rows=[]
    for line in block.splitlines():
        line=line.strip()
        if not line.startswith('|') or re.fullmatch(r'\|[\s:|-]+\|',line):
            continue
        cells=[c.strip() for c in line.strip('|').split('|')]
        rows.append(cells)
    if not rows:
        return Spacer(1,0)
    width=(A4[0]-84)/len(rows[0])
    data=[[Paragraph(escape(c).replace('**',''),head if i==0 else cell) for c in r] for i,r in enumerate(rows)]
    table=Table(data,colWidths=[width]*len(rows[0]),hAlign='LEFT')
    table.setStyle(TableStyle([
        ('LINEBELOW',(0,0),(-1,0),0.8,colors.HexColor('#315c9c')),
        ('LINEBELOW',(0,1),(-1,-2),0.25,colors.HexColor('#d7dee8')),
        ('VALIGN',(0,0),(-1,-1),'TOP'),
        ('TOPPADDING',(0,0),(-1,-1),3),('BOTTOMPADDING',(0,0),(-1,-1),3),
        ('LEFTPADDING',(0,0),(-1,-1),4),('RIGHTPADDING',(0,0),(-1,-1),4)]))
    return table


def main():
    output=ROOT/'output/pdf'
    output.mkdir(parents=True,exist_ok=True)
    rendered=ROOT/'tmp/pdfs'
    rendered.mkdir(parents=True,exist_ok=True)
    styles=getSampleStyleSheet()
    styles.add(ParagraphStyle('ReportBody',fontName='Helvetica',fontSize=10,leading=13.5,spaceAfter=8,textColor=colors.HexColor('#24344b')))
    styles['Heading1'].fontSize=18
    styles['Heading1'].leading=23
    styles['Heading1'].textColor=colors.HexColor('#315c9c')
    styles['Heading2'].fontSize=12
    styles['Heading2'].leading=16
    styles['Heading2'].spaceBefore=12
    styles['Heading2'].textColor=colors.HexColor('#315c9c')
    styles['Heading2'].keepWithNext=True
    styles['Heading3'].textColor=colors.HexColor('#315c9c')
    styles['Heading3'].fontSize=11
    styles['Heading3'].spaceBefore=10
    styles['Heading3'].keepWithNext=True
    story=[]
    text=(ROOT/'docs/report.md').read_text(encoding='utf-8')
    text=text.replace('—','-').replace('–','-').replace('≥','>=').replace('→','->')
    for block in text.split('\n\n'):
        block=block.strip()
        if not block:
            continue
        if block.startswith('# '):
            story.append(Paragraph(escape(block[2:]),styles['Heading1']))
        elif block.startswith('### '):
            story.append(Paragraph(escape(block[4:]),styles['Heading3']))
        elif block.startswith('## '):
            story.append(Paragraph(escape(block[3:]),styles['Heading2']))
        elif block.startswith('|'):
            story.append(markdown_table(block,styles))
        elif block.startswith('- '):
            for line in block.splitlines():
                story.append(Paragraph(escape(line.removeprefix('- ')),styles['ReportBody'],bulletText='-'))
        else:
            story.append(Paragraph(escape(re.sub(r'\s+',' ',block).replace('`','')),styles['ReportBody']))
    story += [PageBreak(),Paragraph('Validation diagnostics',styles['Heading1']),
              Paragraph('All figures derive from the saved 800-ticket validation evaluation.',styles['ReportBody']),
              Image(str(ROOT/'experiments/figures/confusion_matrix.png'),width=400,height=320),
              Spacer(1,15),Image(str(ROOT/'experiments/figures/calibration_and_risk.png'),width=465,height=186)]
    def footer(canvas,doc):
        canvas.setFont('Helvetica',8)
        canvas.setFillColor(colors.HexColor('#63748d'))
        canvas.drawString(42,28,f'TensorForge 2.0 | Synthetic workshop benchmark | {date.today().isoformat()}')
        canvas.drawRightString(A4[0]-42,28,f'{doc.page}')
    path=output/'tensorforge_report.pdf'
    SimpleDocTemplate(str(path),pagesize=A4,rightMargin=42,leftMargin=42,topMargin=42,bottomMargin=45).build(story,onFirstPage=footer,onLaterPages=footer)
    reader=PdfReader(path)
    if len(reader.pages)>5:
        raise AssertionError(f'Report exceeds five pages: {len(reader.pages)}')
    if sum(len(page.extract_text() or '') for page in reader.pages)<3000:
        raise AssertionError('Missing report text')
    pdf=pdfium.PdfDocument(path)
    for i,page in enumerate(pdf):
        bitmap=page.render(scale=1.25)
        bitmap.to_pil().save(rendered/f'report-page-{i+1}.png')
    print(f'Exported report: {len(reader.pages)} pages; rendered every page to tmp/pdfs for visual inspection.')


if __name__=='__main__':
    main()
