# rag.py - Core RAG Pipeline

import os
import shutil
from pathlib import Path

from langchain_community.document_loaders import TextLoader, PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain.prompts import PromptTemplate
from langchain.chains import RetrievalQA
from langchain_community.vectorstores import FAISS


def load_document(file_path: str):
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Document not found at: {file_path}")
    if path.suffix.lower() == ".pdf":
        loader = PyPDFLoader(str(path))
    else:
        loader = TextLoader(str(path), encoding="utf-8")
    docs = loader.load()
    print(f"[RAG] Loaded {len(docs)} document(s) from '{file_path}'")
    return docs


def split_documents(documents, chunk_size=800, chunk_overlap=100):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    chunks = splitter.split_documents(documents)
    print(f"[RAG] Created {len(chunks)} chunks")
    return chunks


def get_embeddings():
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise EnvironmentError("GOOGLE_API_KEY is not set in .env file!")
    for model in ["models/gemini-embedding-2", "models/text-embedding-004", "models/embedding-001"]:
        try:
            emb = GoogleGenerativeAIEmbeddings(model=model, google_api_key=api_key)
            emb.embed_query("test")
            print(f"[RAG] Using embedding model: {model}")
            return emb
        except Exception:
            continue
    raise RuntimeError("No working embedding model found. Check your API key.")


def create_vector_store(chunks, persist_directory="./faiss_db"):
    embeddings = get_embeddings()
    vector_store = FAISS.from_documents(chunks, embeddings)
    vector_store.save_local(persist_directory)
    print(f"[RAG] Vector store saved ({len(chunks)} vectors)")
    return vector_store


def load_vector_store(persist_directory="./faiss_db"):
    embeddings = get_embeddings()
    vector_store = FAISS.load_local(
        persist_directory, embeddings,
        allow_dangerous_deserialization=True,
    )
    print(f"[RAG] Loaded vector store from disk")
    return vector_store


def build_rag_chain(vector_store, k=4):
    api_key = os.getenv("GOOGLE_API_KEY")

    retriever = vector_store.as_retriever(
        search_type="similarity",
        search_kwargs={"k": k},
    )

    llm = None
    for model in ["gemini-3-flash-preview", "gemini-1.5-flash", "gemini-pro"]:
        try:
            llm = ChatGoogleGenerativeAI(
                model=model,
                google_api_key=api_key,
                temperature=0.3,
                convert_system_message_to_human=True,
            )
            print(f"[RAG] Using LLM: {model}")
            break
        except Exception:
            continue

    if not llm:
        raise RuntimeError("No working LLM model found.")

    # Simple prompt with only {context} and {question}
    # No chat_history in prompt template to avoid LangChain key errors
    prompt_template = """You are a helpful AI assistant like ChatGPT.

You have access to a knowledge base shown in the context below.
- If the question relates to the context, use it to give a precise answer.
- If the context does not contain the answer, use your own general knowledge to help.
- Always be helpful, friendly, and give detailed answers.
- If asked about code, provide working code examples.
- If asked general questions like jokes, greetings, math — answer them normally.

Knowledge Base Context:
{context}

Question: {question}

Helpful Answer:"""

    prompt = PromptTemplate(
        template=prompt_template,
        input_variables=["context", "question"],
    )

    rag_chain = RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=retriever,
        return_source_documents=True,
        chain_type_kwargs={"prompt": prompt},
    )

    print("[RAG] RAG chain ready")
    return rag_chain, llm


def ask_question(rag_chain, llm, question: str, chat_history: list = None) -> dict:
    # Build conversation context and append to question for memory
    if chat_history and len(chat_history) > 0:
        history_text = ""
        for msg in chat_history[-6:]:
            role = "User" if msg["role"] == "user" else "Assistant"
            history_text += f"{role}: {msg['text']}\n"
        # Append history as part of the question for context
        full_question = f"Previous conversation:\n{history_text}\nCurrent question: {question}"
    else:
        full_question = question

    result = rag_chain.invoke({"query": full_question})

    answer = result["result"]
    sources = result.get("source_documents", [])
    source_previews = [doc.page_content[:200] + "..." for doc in sources]

    return {
        "answer": answer,
        "sources": source_previews,
        "num_sources": len(sources),
    }


def initialize_rag_pipeline(
    document_path="./data/sample.txt",
    chroma_dir="./faiss_db",
    force_reindex=False,
):
    faiss_path = Path(chroma_dir)

    if faiss_path.exists() and not force_reindex:
        print("[RAG] Found existing vector store - loading from disk (fast)...")
        vector_store = load_vector_store(chroma_dir)
    else:
        if force_reindex and faiss_path.exists():
            shutil.rmtree(faiss_path)
        print("[RAG] Building vector store from scratch (first run ~30s)...")
        docs = load_document(document_path)
        chunks = split_documents(docs)
        vector_store = create_vector_store(chunks, chroma_dir)

    return build_rag_chain(vector_store)