import { useState } from "react";
import { apiFetch } from "../api/client";
import { useAuth } from "../context/AuthContext";

export default function QA() {
  const { role } = useAuth();
  const [q, setQ] = useState("");
  const [result, setResult] = useState<any>(null);
  async function ask() {
    setResult(await apiFetch("/qa/ask", { method: "POST", body: JSON.stringify({ question: q }) }));
  }
  async function answer(id: number) {
    const ans = prompt("输入回答");
    if (!ans) return;
    await apiFetch(`/qa/${id}/answer`, { method: "POST", body: JSON.stringify({ answer: ans }) });
    alert("已回答并回流知识库");
  }
  return (
    <div style={{ padding: 40 }}>
      <h2>答疑</h2>
      <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="输入你的问题" />
      <button onClick={ask}>提问</button>
      {result && (
        <div>
          {result.needs_human ? (
            <p>暂无答案，已转技术人员（问题ID={result.id}）</p>
          ) : (
            <p>{result.answer}</p>
          )}
          {result.needs_human && (role === "tech" || role === "admin") && (
            <button onClick={() => answer(result.id)}>作答</button>
          )}
        </div>
      )}
    </div>
  );
}
