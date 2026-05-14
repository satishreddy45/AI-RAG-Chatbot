# RAG Chatbot — ChatGPT-like AI powered by Gemini + LangChain + FAISS

A production-ready RAG chatbot for interview demonstration.

## Features
- ✅ RAG pipeline (LangChain + FAISS + Gemini)
- ✅ Works like ChatGPT — answers ANY question
- ✅ Conversation memory (remembers last 10 messages)
- ✅ Upload your own PDF/TXT document
- ✅ Typing animation (word by word like ChatGPT)
- ✅ Chat history stored in MongoDB
- ✅ Copy answer button
- ✅ Dark/Light mode
- ✅ FastAPI backend with auto docs
- ✅ React frontend

## Project Structure
```
rag-chatgpt/
├── backend/
│   ├── main.py           ← FastAPI server
│   ├── rag.py            ← RAG pipeline
│   ├── db.py             ← MongoDB
│   ├── requirements.txt  ← Python packages
│   ├── .env.example      ← API key template
│   └── data/
│       └── sample.txt    ← Knowledge base
└── frontend/
    ├── package.json
    └── src/
        ├── App.js         ← Chat UI
        └── App.css        ← Styles
```

## Setup & Run

### Step 1 — Get Gemini API Key
Go to https://aistudio.google.com/app/apikey and create a free key.

### Step 2 — Backend Setup
```bash
cd backend
python -m venv venv

# Mac/Linux:
source venv/bin/activate
# Windows:
venv\Scripts\activate

pip install -r requirements.txt
pip install onnxruntime faiss-cpu  # extra packages needed on Windows
```

### Step 3 — Create .env file
Create a file called `.env` inside the `backend/` folder:
```
GOOGLE_API_KEY=your_key_here
MONGO_URI=mongodb://localhost:27017
DOCUMENT_PATH=./data/sample.txt
```

### Step 4 — Run Backend (Terminal 1)
```bash
cd backend
venv\Scripts\activate        # Windows
source venv/bin/activate     # Mac/Linux
python -m uvicorn main:app --reload --port 8000
```

### Step 5 — Run Frontend (Terminal 2)
```bash
cd frontend
npm install
npm start
```

Browser opens at http://localhost:3000

## API Endpoints
- `POST /ask` — Ask a question (with chat history)
- `GET /health` — Health check
- `GET /history` — Recent chat history
- `POST /upload` — Upload PDF/TXT document
- `POST /reindex` — Re-embed document
- `GET /docs` — Interactive API documentation

## Sample Questions
- What is Retrieval Augmented Generation?
- How do embeddings work?
- What is machine learning?
- What is Google Gemini?
- Who is Elon Musk? (general knowledge)
- Tell me a joke (general knowledge)

## Interview Explanation
"I built a full-stack RAG chatbot using LangChain, Google Gemini, FAISS vector database,
FastAPI backend, and React frontend. It supports document upload, conversation memory,
chat history in MongoDB, and works like ChatGPT — answering from both the knowledge base
and general knowledge. The RAG pipeline reduces hallucination by grounding answers in
retrieved document chunks."
