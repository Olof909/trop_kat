import io
import json
import os
import tempfile
from pathlib import Path

import httpx
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi import Request
from pydantic import BaseModel

from services.docx_parser import parse_bylaws
from services.docx_generator import generate_docx
from services.diff_service import compute_diff

app = FastAPI(title="Τροποποίηση Καταστατικών")

templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")


class Article(BaseModel):
    id: int
    title: str
    content: str


class GenerateRequest(BaseModel):
    articles: list[Article]
    document_title: str = "Καταστατικό"


class DiffRequest(BaseModel):
    original: list[Article]
    modified: list[Article]


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    articles: list[Article] = []


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/api/upload")
async def upload_docx(file: UploadFile = File(...)):
    if not file.filename.endswith(".docx"):
        raise HTTPException(status_code=400, detail="Αποδεκτά μόνο αρχεία .docx")

    content = await file.read()
    try:
        articles = parse_bylaws(io.BytesIO(content))
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Σφάλμα ανάλυσης αρχείου: {str(e)}")

    return {"filename": file.filename, "articles": articles}


@app.post("/api/generate")
async def generate(req: GenerateRequest):
    try:
        docx_bytes = generate_docx(req.articles, req.document_title)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Σφάλμα δημιουργίας αρχείου: {str(e)}")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp:
        tmp.write(docx_bytes)
        tmp_path = tmp.name

    return FileResponse(
        tmp_path,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename="τροποποιημένο_καταστατικό.docx",
    )


@app.post("/api/diff")
async def diff(req: DiffRequest):
    result = compute_diff(req.original, req.modified)
    return {"diff": result}


@app.post("/api/chat")
async def chat(req: ChatRequest):
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="OPENROUTER_API_KEY δεν έχει οριστεί")

    system_content = (
        "Είσαι ειδικός βοηθός για την επεξεργασία και τροποποίηση καταστατικών εταιρειών στην Ελλάδα. "
        "Βοηθάς τον χρήστη να βελτιώσει το περιεχόμενο άρθρων, να αναδιατυπώσει κείμενα νομικής φύσης, "
        "και να απαντάς σε ερωτήσεις σχετικά με το καταστατικό. Απαντάς πάντα στα ελληνικά."
    )

    if req.articles:
        articles_text = "\n\n".join(
            f"Άρθρο {a.id} – {a.title}:\n{a.content}" for a in req.articles
        )
        system_content += f"\n\nΤρέχον καταστατικό που επεξεργάζεται ο χρήστης:\n\n{articles_text}"

    messages = [{"role": "system", "content": system_content}]
    messages.extend({"role": m.role, "content": m.content} for m in req.messages)

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json={"model": "openai/gpt-4o-mini", "messages": messages},
            )
        if resp.status_code != 200:
            raise HTTPException(status_code=502, detail=f"Σφάλμα AI API: {resp.text}")
        reply = resp.json()["choices"][0]["message"]["content"]
        return {"reply": reply}
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Timeout από το AI API")
