import { useState, useRef, useEffect } from "react";
import "./App.css";

const API = "http://localhost:8000";

const SAMPLES = [
  "What is Retrieval Augmented Generation?",
  "How do embeddings work?",
  "What is machine learning?",
  "What is Google Gemini?",
  "How does RAG reduce hallucination?",
  "What are neural networks?",
  "Explain deep learning simply",
  "What is FAISS?",
];

function now() {
  return new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function extractError(e) {
  if (!e) return "Unknown error";
  if (typeof e === "string") return e;
  if (e.message) return e.message.includes("fetch") ? "Cannot reach backend on port 8000. Is it running?" : e.message;
  if (e.detail) return String(e.detail);
  try { return JSON.stringify(e); } catch { return "Unknown error"; }
}

// Typing animation — text appears word by word like ChatGPT
function TypingText({ text }) {
  const [shown, setShown] = useState("");
  useEffect(() => {
    setShown("");
    let i = 0;
    const t = setInterval(() => {
      i++;
      setShown(text.slice(0, i));
      if (i >= text.length) clearInterval(t);
    }, 8);
    return () => clearInterval(t);
  }, [text]);
  return <span style={{ whiteSpace: "pre-wrap", wordBreak: "break-word" }}>{shown}</span>;
}

export default function App() {
  const [messages, setMessages] = useState([
    {
      role: "assistant",
      text: "Hi! I'm your AI assistant powered by RAG + Gemini. I can answer questions from my knowledge base AND general questions — just like ChatGPT. You can also upload your own PDF or TXT file to chat with it!",
      time: now(),
      isNew: false,
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [openSources, setOpenSources] = useState({});
  const [history, setHistory] = useState([]);
  const [showHistory, setShowHistory] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadMsg, setUploadMsg] = useState("");
  const [darkMode, setDarkMode] = useState(true);
  const [copiedIdx, setCopiedIdx] = useState(null);
  const [currentDoc, setCurrentDoc] = useState("sample.txt");

  const bottomRef = useRef(null);
  const inputRef = useRef(null);
  const fileRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  useEffect(() => { fetchHistory(); }, []);

  async function fetchHistory() {
    try {
      const res = await fetch(`${API}/history?limit=20`);
      const data = await res.json();
      setHistory(data.chats || []);
    } catch {}
  }

  async function sendQuestion(question) {
    if (!question.trim() || loading) return;
    setError("");
    setLoading(true);
    setInput("");

    setMessages(prev => [...prev, { role: "user", text: question, time: now(), isNew: false }]);

    // Send last 10 messages as conversation history
    const chatHistory = messages.slice(-10).map(m => ({ role: m.role, text: m.text }));

    try {
      const res = await fetch(`${API}/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question, chat_history: chatHistory }),
      });

      if (!res.ok) {
        let errMsg = `Server error ${res.status}`;
        try { const d = await res.json(); errMsg = d.detail || errMsg; } catch {}
        throw new Error(String(errMsg));
      }

      const data = await res.json();
      setMessages(prev => [...prev, {
        role: "assistant",
        text: data.answer,
        sources: data.sources,
        num_sources: data.num_sources,
        time: now(),
        isNew: true,
      }]);
      fetchHistory();
    } catch (e) {
      const msg = extractError(e);
      setError(msg);
      setMessages(prev => [...prev, { role: "error", text: msg, time: now(), isNew: false }]);
    } finally {
      setLoading(false);
      inputRef.current?.focus();
    }
  }

  async function handleUpload(e) {
    const file = e.target.files[0];
    if (!file) return;
    setUploading(true);
    setUploadMsg("⏳ Uploading and indexing...");

    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await fetch(`${API}/upload`, { method: "POST", body: formData });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Upload failed");
      setUploadMsg(`✅ Indexed!`);
      setCurrentDoc(file.name);
      setMessages(prev => [...prev, {
        role: "assistant",
        text: `📄 Document "${file.name}" uploaded and indexed successfully! Now ask me anything about it.`,
        time: now(),
        isNew: true,
      }]);
    } catch (e) {
      setUploadMsg(`❌ ${extractError(e)}`);
    } finally {
      setUploading(false);
      setTimeout(() => setUploadMsg(""), 5000);
      fileRef.current.value = "";
    }
  }

  function copyText(text, idx) {
    navigator.clipboard.writeText(text);
    setCopiedIdx(idx);
    setTimeout(() => setCopiedIdx(null), 2000);
  }

  function handleKey(e) {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendQuestion(input.trim()); }
  }

  function clearChat() {
    setMessages([{ role: "assistant", text: "Chat cleared! Ask me anything.", time: now(), isNew: false }]);
    setError("");
  }

  return (
    <div className={`shell ${darkMode ? "dark" : "light"}`}>
      {/* ── Header ── */}
      <header className="topbar">
        <div className="brand">
          <span className="brand-icon">◈</span>
          <div>
            <div className="brand-name">RAG Chatbot</div>
            <div className="brand-sub">Gemini · LangChain · FAISS · FastAPI · MongoDB</div>
          </div>
        </div>
        <div className="header-right">
          <span className="doc-badge">📄 {currentDoc}</span>
          <button className="icon-btn" onClick={clearChat} title="Clear chat">🗑️</button>
          <button className="icon-btn" onClick={() => { setShowHistory(!showHistory); fetchHistory(); }} title="History">🕓</button>
          <button className="icon-btn" onClick={() => setDarkMode(!darkMode)} title="Toggle theme">{darkMode ? "☀️" : "🌙"}</button>
          <div className="status-pill"><span className="dot" />Live</div>
        </div>
      </header>

      <div className="body">
        {/* ── Sidebar ── */}
        <aside className="sidebar">
          {/* Upload */}
          <div className="panel">
            <div className="panel-title">📁 Upload Document</div>
            <p className="upload-hint">Upload your own PDF or TXT to chat with it</p>
            <button className="upload-btn" onClick={() => fileRef.current.click()} disabled={uploading}>
              {uploading ? "⏳ Indexing..." : "📤 Upload File"}
            </button>
            <input ref={fileRef} type="file" accept=".pdf,.txt" style={{ display: "none" }} onChange={handleUpload} />
            {uploadMsg && <p className="upload-msg">{uploadMsg}</p>}
          </div>

          {/* History or Samples */}
          {showHistory ? (
            <div className="panel">
              <div className="panel-title">🕓 Recent Chats</div>
              {history.length === 0
                ? <p className="no-history">No history yet</p>
                : history.map((h, i) => (
                  <button key={i} className="sample" onClick={() => sendQuestion(h.question)} disabled={loading}>
                    {h.question.slice(0, 50)}{h.question.length > 50 ? "..." : ""}
                  </button>
                ))
              }
            </div>
          ) : (
            <div className="panel">
              <div className="panel-title">💡 Try Asking</div>
              {SAMPLES.map((q, i) => (
                <button key={i} className="sample" onClick={() => sendQuestion(q)} disabled={loading}>{q}</button>
              ))}
            </div>
          )}

          {/* How it works */}
          <div className="panel">
            <div className="panel-title">⚡ How RAG Works</div>
            <div className="steps">
              {[
                ["1", "Embed", "Question → vector"],
                ["2", "Retrieve", "Similar chunks fetched from FAISS"],
                ["3", "Generate", "Gemini answers using context"],
              ].map(([n, t, d]) => (
                <div className="step" key={n}>
                  <span className="step-n">{n}</span>
                  <div><b>{t}</b><p>{d}</p></div>
                </div>
              ))}
            </div>
          </div>

          {/* Stack */}
          <div className="panel">
            <div className="panel-title">🛠 Tech Stack</div>
            <div className="tags">
              {["Gemini", "LangChain", "FAISS", "FastAPI", "MongoDB", "React"].map(t => (
                <span className="tag" key={t}>{t}</span>
              ))}
            </div>
          </div>
        </aside>

        {/* ── Chat ── */}
        <main className="chat">
          <div className="messages">
            {messages.map((m, i) => (
              <div key={i} className={`row ${m.role}`}>
                <div className="avatar">
                  {m.role === "user" ? "👤" : m.role === "error" ? "⚠️" : "🤖"}
                </div>
                <div className="bubble-wrap">
                  <div className={`bubble ${m.role}`}>
                    {m.role === "assistant"
                      ? (m.isNew ? <TypingText text={m.text} /> : <span style={{ whiteSpace: "pre-wrap" }}>{m.text}</span>)
                      : <span style={{ whiteSpace: "pre-wrap" }}>{m.text}</span>
                    }
                    {m.role === "assistant" && (
                      <button className="copy-btn" onClick={() => copyText(m.text, i)} title="Copy">
                        {copiedIdx === i ? "✅" : "⧉"}
                      </button>
                    )}
                  </div>

                  {m.sources && m.sources.length > 0 && (
                    <div className="sources">
                      <button className="src-toggle" onClick={() => setOpenSources(p => ({ ...p, [i]: !p[i] }))}>
                        📄 {openSources[i] ? "Hide" : "Show"} {m.num_sources} source(s) {openSources[i] ? "▲" : "▼"}
                      </button>
                      {openSources[i] && (
                        <div className="src-list">
                          {m.sources.map((s, si) => (
                            <div className="src-item" key={si}>
                              <span className="src-n">#{si + 1}</span>
                              <span className="src-text">{s}</span>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                  <span className="time">{m.time}</span>
                </div>
              </div>
            ))}

            {loading && (
              <div className="row assistant">
                <div className="avatar">🤖</div>
                <div className="bubble-wrap">
                  <div className="bubble assistant loading">
                    <span /><span /><span />
                    <em>Thinking...</em>
                  </div>
                </div>
              </div>
            )}
            <div ref={bottomRef} />
          </div>

          {/* Input */}
          <div className="input-area">
            {error && (
              <div className="err-bar">
                ⚠️ {error}
                <button onClick={() => setError("")}>✕</button>
              </div>
            )}
            <div className="input-row">
              <textarea
                ref={inputRef}
                className="input"
                rows={2}
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={handleKey}
                placeholder="Ask anything — from docs or general knowledge..."
                disabled={loading}
              />
              <button
                className="send"
                onClick={() => sendQuestion(input.trim())}
                disabled={loading || !input.trim()}
              >
                {loading ? "⏳" : "Send ↗"}
              </button>
            </div>
            <div className="hint">Enter to send · Shift+Enter for new line · Upload docs to customize knowledge</div>
          </div>
        </main>
      </div>
    </div>
  );
}
