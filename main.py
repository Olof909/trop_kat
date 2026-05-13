import io
import json
import tempfile
from pathlib import Path

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
