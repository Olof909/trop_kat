import difflib


def _article_map(articles: list) -> dict[int, dict]:
    result = {}
    for a in articles:
        aid = a.id if hasattr(a, "id") else a["id"]
        result[aid] = {
            "id": aid,
            "title": a.title if hasattr(a, "title") else a["title"],
            "content": a.content if hasattr(a, "content") else a["content"],
        }
    return result


def compute_diff(original: list, modified: list) -> list[dict]:
    orig_map = _article_map(original)
    mod_map = _article_map(modified)

    all_ids = sorted(set(orig_map) | set(mod_map))
    results = []

    for aid in all_ids:
        orig = orig_map.get(aid)
        mod = mod_map.get(aid)

        if orig is None:
            results.append(
                {
                    "id": aid,
                    "status": "added",
                    "title": mod["title"],
                    "content_diff": _inline_diff("", mod["content"]),
                }
            )
        elif mod is None:
            results.append(
                {
                    "id": aid,
                    "status": "deleted",
                    "title": orig["title"],
                    "content_diff": _inline_diff(orig["content"], ""),
                }
            )
        elif orig["content"] != mod["content"] or orig["title"] != mod["title"]:
            results.append(
                {
                    "id": aid,
                    "status": "modified",
                    "title": mod["title"],
                    "title_changed": orig["title"] != mod["title"],
                    "old_title": orig["title"],
                    "content_diff": _inline_diff(orig["content"], mod["content"]),
                }
            )
        else:
            results.append(
                {
                    "id": aid,
                    "status": "unchanged",
                    "title": orig["title"],
                    "content_diff": [],
                }
            )

    return results


def _inline_diff(old: str, new: str) -> list[dict]:
    old_lines = old.splitlines(keepends=True)
    new_lines = new.splitlines(keepends=True)

    differ = difflib.Differ()
    diff = list(differ.compare(old_lines, new_lines))

    result = []
    for line in diff:
        tag = line[:2]
        text = line[2:]
        if tag == "  ":
            result.append({"type": "equal", "text": text.rstrip("\n")})
        elif tag == "- ":
            result.append({"type": "removed", "text": text.rstrip("\n")})
        elif tag == "+ ":
            result.append({"type": "added", "text": text.rstrip("\n")})
    return result
