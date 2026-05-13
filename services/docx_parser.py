import re
from io import BytesIO
from docx import Document

# Matches: "Άρθρο 1", "ΑΡΘΡΟ 1", "Άρθρο 1.", "Άρθρο 1 -", "ΑΡΘΡΟ 1:"
ARTICLE_HEADER_RE = re.compile(
    r"^\s*[ΆΑ][ρΡ][θΘ][ρΡ][οΟ]\s+(\d+)[\.\:\-\s]*(.*)",
    re.IGNORECASE | re.UNICODE,
)


def _is_article_header(text: str) -> re.Match | None:
    return ARTICLE_HEADER_RE.match(text.strip())


def parse_bylaws(file: BytesIO) -> list[dict]:
    doc = Document(file)
    articles: list[dict] = []
    current_article: dict | None = None
    current_lines: list[str] = []
    preamble_lines: list[str] = []

    for para in doc.paragraphs:
        text = para.text.strip()
        if not text:
            if current_article is not None:
                current_lines.append("")
            continue

        match = _is_article_header(text)
        if match:
            # Save previous article
            if current_article is not None:
                current_article["content"] = "\n".join(current_lines).strip()
                articles.append(current_article)
            elif preamble_lines:
                # Save preamble as article 0
                articles.append(
                    {
                        "id": 0,
                        "title": "Προοίμιο",
                        "content": "\n".join(preamble_lines).strip(),
                    }
                )

            article_num = int(match.group(1))
            inline_title = match.group(2).strip().strip("-:").strip()
            current_article = {
                "id": article_num,
                "title": inline_title or f"Άρθρο {article_num}",
            }
            current_lines = []
        else:
            if current_article is None:
                preamble_lines.append(text)
            else:
                current_lines.append(text)

    # Flush last article
    if current_article is not None:
        current_article["content"] = "\n".join(current_lines).strip()
        articles.append(current_article)
    elif preamble_lines and not articles:
        # Document has no articles — treat all paragraphs as a single block
        articles.append(
            {"id": 1, "title": "Άρθρο 1", "content": "\n".join(preamble_lines).strip()}
        )

    return articles
