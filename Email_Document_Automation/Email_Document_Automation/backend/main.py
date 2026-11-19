from __future__ import annotations

import uuid
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr, Field

from .config import get_settings
from .documents import (
    build_docx,
    build_pdf,
    extract_text_from_docx,
    extract_text_from_pdf,
)
from .email_service import send_email, smtp_configured
from .llm import LLMError, chat_completion

settings = get_settings()
app = FastAPI(title=settings.app_name, version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DOCUMENTS: dict[str, dict] = {}
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"

DocType = Literal["email", "letter", "application", "report", "summary", "document"]
Tone = Literal["professional", "formal", "friendly", "persuasive", "concise"]


class GenerateRequest(BaseModel):
    doc_type: DocType = "email"
    tone: Tone = "professional"
    topic: str = Field(..., min_length=3, max_length=2000)
    recipient: str = Field(default="", max_length=200)
    extra_context: str = Field(default="", max_length=5000)


class GenerateResponse(BaseModel):
    document_id: str
    title: str
    content: str
    doc_type: DocType
    tone: Tone


class SummarizeTextRequest(BaseModel):
    text: str = Field(..., min_length=20, max_length=50000)
    mode: Literal["summary", "extract"] = "summary"


class SendEmailRequest(BaseModel):
    to_email: EmailStr
    subject: str = Field(..., min_length=1, max_length=200)
    body: str = Field(..., min_length=1, max_length=20000)


@app.get("/api/health")
async def health() -> dict:
    configured = bool(settings.openrouter_api_key) and not settings.openrouter_api_key.startswith(
        "your_"
    )
    return {
        "status": "ok",
        "app": settings.app_name,
        "llm_configured": configured,
        "model": settings.openrouter_model,
        "smtp_configured": smtp_configured(),
    }


@app.post("/api/generate", response_model=GenerateResponse)
async def generate_document(payload: GenerateRequest) -> GenerateResponse:
    prompt = f"""Write a high-quality {payload.doc_type} in a {payload.tone} tone.
Topic/purpose: {payload.topic}
Recipient: {payload.recipient or "N/A"}
Extra context: {payload.extra_context or "None"}

Requirements:
- Output polished ready-to-use text.
- For emails, include Subject line on the first line as "Subject: ...".
- For letters/applications, include proper salutations and closing.
- Do not use markdown fences.
"""
    try:
        content = await chat_completion(
            [
                {
                    "role": "system",
                    "content": "You are an expert business writing assistant for emails and documents.",
                },
                {"role": "user", "content": prompt},
            ]
        )
    except LLMError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    title = f"{payload.doc_type.title()}: {payload.topic[:60]}"
    document_id = str(uuid.uuid4())
    DOCUMENTS[document_id] = {"title": title, "content": content, "doc_type": payload.doc_type}
    return GenerateResponse(
        document_id=document_id,
        title=title,
        content=content,
        doc_type=payload.doc_type,
        tone=payload.tone,
    )


@app.post("/api/summarize-text")
async def summarize_text(payload: SummarizeTextRequest) -> dict:
    if payload.mode == "extract":
        instruction = (
            "Extract the most important information as a bullet list of facts, dates, names, "
            "amounts, decisions, and action items."
        )
    else:
        instruction = "Write a clear, structured summary with key takeaways."

    try:
        result = await chat_completion(
            [
                {"role": "system", "content": "You analyze and summarize documents accurately."},
                {
                    "role": "user",
                    "content": f"{instruction}\n\nDocument text:\n{payload.text[:40000]}",
                },
            ]
        )
    except LLMError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    document_id = str(uuid.uuid4())
    title = "Document Summary" if payload.mode == "summary" else "Extracted Information"
    DOCUMENTS[document_id] = {"title": title, "content": result, "doc_type": "summary"}
    return {"document_id": document_id, "title": title, "content": result, "mode": payload.mode}


@app.post("/api/summarize-file")
async def summarize_file(
    file: UploadFile = File(...),
    mode: Literal["summary", "extract"] = "summary",
) -> dict:
    filename = (file.filename or "").lower()
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    try:
        if filename.endswith(".pdf"):
            text = extract_text_from_pdf(data)
        elif filename.endswith(".docx"):
            text = extract_text_from_docx(data)
        else:
            raise HTTPException(status_code=400, detail="Only PDF and DOCX uploads are supported.")
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Failed to read document: {exc}") from exc

    if not text or len(text.strip()) < 20:
        raise HTTPException(status_code=400, detail="Could not extract enough text from the file.")

    return await summarize_text(SummarizeTextRequest(text=text, mode=mode))


@app.get("/api/export/{document_id}/{fmt}")
async def export_document(document_id: str, fmt: str) -> Response:
    doc = DOCUMENTS.get(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found. Generate one first.")

    fmt = fmt.lower()
    title = doc["title"]
    content = doc["content"]
    if fmt == "pdf":
        payload = build_pdf(title, content)
        return Response(
            content=payload,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="document_{document_id[:8]}.pdf"'},
        )
    if fmt in {"docx", "doc"}:
        payload = build_docx(title, content)
        return Response(
            content=payload,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": f'attachment; filename="document_{document_id[:8]}.docx"'},
        )
    raise HTTPException(status_code=400, detail="Format must be pdf or docx.")


@app.post("/api/send-email")
async def api_send_email(payload: SendEmailRequest) -> dict:
    try:
        return send_email(payload.to_email, payload.subject, payload.body)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Failed to send email: {exc}") from exc


@app.get("/")
async def serve_index() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "index.html")


if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")
