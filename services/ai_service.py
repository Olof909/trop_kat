import json
import os
from openai import OpenAI

_client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ["OPENROUTER_API_KEY"],
)

MODEL = os.environ.get("OPENROUTER_MODEL", "openai/gpt-4o-mini")

_SYSTEM_PROMPT = (
    "Είσαι νομικός βοηθός που εξειδικεύεται στη σύνταξη και τροποποίηση καταστατικών "
    "ελληνικών εταιρειών. Ακολουθείς πάντα τις οδηγίες του χρήστη και επιστρέφεις μόνο "
    "τα άρθρα που χρειάζονται αλλαγή, με το ακριβές νέο τους περιεχόμενο."
)

_MODIFY_TOOL = {
    "type": "function",
    "function": {
        "name": "apply_modifications",
        "description": (
            "Εφαρμόζει τις ζητούμενες τροποποιήσεις στα άρθρα του καταστατικού. "
            "Επίστρεψε μόνο τα άρθρα που άλλαξαν."
        ),
        "parameters": {
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

    response = _client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        tools=[_MODIFY_TOOL],
        tool_choice={"type": "function", "function": {"name": "apply_modifications"}},
    )

    message = response.choices[0].message
    if message.tool_calls:
        args = json.loads(message.tool_calls[0].function.arguments)
        changed = {a["id"]: a for a in args["modified_articles"]}
        return [changed.get(a["id"], a) for a in articles]

    return articles
