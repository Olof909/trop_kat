from io import BytesIO
from docx import Document
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH


def generate_docx(articles: list, document_title: str) -> bytes:
    doc = Document()

    # Document title
    title_para = doc.add_paragraph()
    title_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = title_para.add_run(document_title)
    run.bold = True
    run.font.size = Pt(16)

    doc.add_paragraph()

    for article in articles:
        article_id = article.id if hasattr(article, "id") else article["id"]
        title = article.title if hasattr(article, "title") else article["title"]
        content = article.content if hasattr(article, "content") else article["content"]

        # Article header
        header_para = doc.add_paragraph()
        if article_id == 0:
            header_text = title
        else:
            header_text = f"Άρθρο {article_id}"
            if title and title != header_text:
                header_text += f" – {title}"

        run = header_para.add_run(header_text)
        run.bold = True
        run.font.size = Pt(12)

        # Article body — preserve line breaks
        for line in content.split("\n"):
            para = doc.add_paragraph(line)
            para.paragraph_format.space_before = Pt(0)

        doc.add_paragraph()

    buf = BytesIO()
    doc.save(buf)
    return buf.getvalue()
