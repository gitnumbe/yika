import { useState } from "react";
import Layout from "../components/Layout";
import { apiFetch } from "../api/client";
import { useAuth } from "../context/AuthContext";
import { useTTS } from "../hooks/useTTS";

export default function QA() {
  const { role } = useAuth();
  const { speak, loading } = useTTS();
  const [q, setQ] = useState("");
  const [result, setResult] = useState<any>(null);

  async function ask() {
    if (!q.trim()) return;
    setResult(await apiFetch("/qa/ask", { method: "POST", body: JSON.stringify({ question: q }) }));
  }

  async function answer(id: number) {
    const ans = prompt("输入回答");
    if (!ans) return;
    await apiFetch(`/qa/${id}/answer`, { method: "POST", body: JSON.stringify({ answer: ans }) });
    alert("已回答并回流知识库");
  }

  const canAnswer = role === "tech" || role === "admin";

  return (
    <Layout>
      <h2 style={{ margin: "0 0 20px", fontSize: 26, color: "#fff" }}>答疑</h2>

      <div className="gate-card">
        <label className="gate-label" htmlFor="qa-input">向 AI 提问（命中直接答，未命中转技术）</label>
        <div style={{ display: "flex", gap: 10 }}>
          <input
            id="qa-input"
            className="gate-input"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="输入你的问题…"
            onKeyDown={(e) => e.key === "Enter" && ask()}
          />
          <button className="gate-btn" onClick={ask} style={{ flexShrink: 0 }}>提问</button>
        </div>
      </div>

      {result && (
        <div className="gate-card">
          {result.needs_human ? (
            <>
              <h3>未命中，已转技术人员</h3>
              <p className="gate-muted">等待技术回答（会回流知识库）。当前问题：{q}</p>
            </>
          ) : (
            <>
              <h3>AI 回答</h3>
              <p style={{ color: "#fff", lineHeight: 1.7 }}>{result.answer}</p>
              <p className="gate-muted">来源：{result.source} · 置信度 {(result.confidence ?? 0).toFixed(2)}</p>
              {result.id && result.answer && (
                <button
                  className="gate-btn gate-btn-ghost"
                  onClick={() => speak(`/qa/${result.id}/tts`)}
                  disabled={loading}
                >
                  {loading ? "合成中…" : "🔊 朗读回答"}
                </button>
              )}
            </>
          )}
        </div>
      )}
    </Layout>
  );
}
