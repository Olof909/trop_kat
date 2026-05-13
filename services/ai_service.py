import json
import anthropic

_client = anthropic.Anthropic()

_SYSTEM_PROMPT = (
    "Είσαι νομικός βοηθός που εξειδικεύεται στη σύνταξη και τροποποίηση καταστατικών "
    "ελληνικών εταιρειών. Ακολουθείς πάντα τις οδηγίες του χρήστη και επιστρέφεις μόνο "
    "τα άρθρα που χρειάζονται αλλαγή, με το ακριβές νέο τους περιεχόμενο."
)

_MODIFY_TOOL = {
    "name": "apply_modifications",
    "description": (
        "Εφαρμόζει τις ζητούμενες τροποποιήσεις στα άρθρα του καταστατικού. "
        "Επίστρεψε μόνο τα άρθρα που άλλαξαν."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "modified_articles": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer", "description": "Αριθμός άρθρου"},
                        "title": {"type": "string", "description": "Τίτλος άρθρου"},
                        "content": {"type": "string", "description": "Νέο περιεχόμενο άρθρου"},
                    },
                    "required": ["id", "title", "content"],
                },
                "description": "Λίστα τροποποιημένων άρθρων",
            }
        },
        "required": ["modified_articles"],
    },
}


def apply_ai_modifications(articles: list[dict], instruction: str) -> list[dict]:
    articles_text = "\n\n".join(
        f"=== Άρθρο {a['id']} – {a['title']} ===\n{a['content']}"
        for a in articles
    )

    user_message = (
        f"Παρακάτω είναι τα άρθρα του καταστατικού:\n\n"
        f"{articles_text}\n\n"
        f"Οδηγία τροποποίησης: {instruction}\n\n"
        "Χρησιμοποίησε το εργαλείο apply_modifications για να επιστρέψεις "
        "μόνο τα άρθρα που χρειάζονται αλλαγή."
    )

    response = _client.messages.create(
        model="claude-opus-4-7",
        max_tokens=8192,
        thinking={"type": "adaptive"},
        system=[
            {
                "type": "text",
                "text": _SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        tools=[_MODIFY_TOOL],
        tool_choice={"type": "tool", "name": "apply_modifications"},
        messages=[{"role": "user", "content": user_message}],
    )

    for block in response.content:
        if block.type == "tool_use" and block.name == "apply_modifications":
            changed = {a["id"]: a for a in block.input["modified_articles"]}
            result = []
            for article in articles:
                aid = article["id"]
                result.append(changed.get(aid, article))
            return result

    return articles
