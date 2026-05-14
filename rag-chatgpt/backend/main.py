# main.py - FastAPI Server
# Run: python -m uvicorn main:app --reload --port 8000

import os
import shutil
from contextlib import asynccontextmanager
from typing import List, Optional
from dotenv import load_dotenv

from fastapi import FastAPI, HTTPException, Query, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from rag import initialize_rag_pipeline, ask_question
from db import save_chat, get_recent_chats, get_chat_count

load_dotenv()

rag_chain = None
llm = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global rag_chain, llm
    print("\n" + "="*50)
    print("  Starting RAG Chatbot API...")
    print("="*50)
    doc_path = os.getenv("DOCUMENT_PATH", "./data/sample.txt")
    rag_chain, llm = initialize_rag_pipeline(
        document_path=doc_path,
        chroma_dir="./faiss_db",
        force_reindex=False,
    )
    print("="*50)
    print("  RAG pipeline ready! Server is live.")
    print("  API Docs: http://localhost:8000/docs")
    print("="*50 + "\n")
    yield
    print("[SHUTDOWN] Goodbye!")


app = FastAPI(
    title="RAG Chatbot API",
    description="ChatGPT-like RAG chatbot powered by Gemini + LangChain + FAISS",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Schemas ──────────────────────────────────────

class ChatMessage(BaseModel):
    role: str
    text: str

class AskRequest(BaseModel):
    question: str
    chat_history: Optional[List[ChatMessage]] = []

class AskResponse(BaseModel):
    question: str
    answer: str
    sources: list[str]
    num_sources: int
    db_id: str


# ── Endpoints ─────────────────────────────────────

@app.get("/")
def root():
    return {
        "status": "running",
        "docs": "http://localhost:8000/docs",
        "usage": "POST /ask with {question, chat_history}",
    }


@app.get("/health")
def health():
    return {
        "status": "healthy" if rag_chain else "initializing",
        "rag_ready": rag_chain is not None,
        "total_chats": get_chat_count(),
    }


@app.post("/ask", response_model=AskResponse)
def ask(request: AskRequest):
    """Main RAG endpoint — answers questions using retrieved context + Gemini"""
    if rag_chain is None:
        raise HTTPException(503, "RAG pipeline not ready. Please wait.")
    try:
        print(f"\n[API] Question: {request.question}")
        history = [{"role": m.role, "text": m.text} for m in (request.chat_history or [])]
        result = ask_question(rag_chain, llm, request.question, history)
        db_id = save_chat(request.question, result["answer"], result["sources"])
        return AskResponse(
            question=request.question,
            answer=result["answer"],
            sources=result["sources"],
            num_sources=result["num_sources"],
            db_id=db_id,
        )
    except Exception as e:
        print(f"[API] Error: {e}")
        raise HTTPException(500, f"Error processing question: {str(e)}")


@app.get("/history")
def history(limit: int = Query(default=20, ge=1, le=100)):
    """Return recent chat history from MongoDB"""
    return {"chats": get_recent_chats(limit)}


@app.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    """Upload a PDF or TXT file and reindex as new knowledge base"""
    global rag_chain, llm

    if not file.filename.endswith((".pdf", ".txt")):
        raise HTTPException(400, "Only .pdf and .txt files are supported.")

    upload_path = f"./data/{file.filename}"
    with open(upload_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    print(f"[UPLOAD] File saved: {upload_path}")

    try:
        rag_chain, llm = initialize_rag_pipeline(
            document_path=upload_path,
            chroma_dir="./faiss_db",
            force_reindex=True,
        )
        return {
            "status": "success",
            "message": f"'{file.filename}' uploaded and indexed successfully!",
            "filename": file.filename,
        }
    except Exception as e:
        raise HTTPException(500, f"Error indexing file: {str(e)}")


@app.post("/reindex")
def reindex():
    """Force re-embed the document. Use after updating data/sample.txt"""
    global rag_chain, llm
    doc_path = os.getenv("DOCUMENT_PATH", "./data/sample.txt")
    rag_chain, llm = initialize_rag_pipeline(doc_path, "./faiss_db", force_reindex=True)
    return {"status": "ok", "message": "Reindexed successfully"}
