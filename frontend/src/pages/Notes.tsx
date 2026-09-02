import { useEffect, useState } from "react";
import Layout from "../components/Layout";
import { apiFetch } from "../api/client";
import { useTTS } from "../hooks/useTTS";

const SCENE_LABEL: Record<string, string> = {
  internal: "内部沟通",
  discussion: "客户需求探索",
};

export default function Notes() {
  const { speak, loading } = useTTS();
  const [notes, setNotes] = useState<any[]>([]);

  async function load() {
    setNotes(await apiFetch("/notes/"));
  }
  useEffect(() => {
    load();
  }, []);

  async function extract(noteId: number) {
    const res = await apiFetch(`/notes/${noteId}/extract`, { method: "POST" });
    const candidates = res.candidates ?? [];
    if (candidates.length === 0) {
      alert("未提炼出候选需求（防幻觉：需人工确认后才落库）");
      return;
    }
    const confirm = window.confirm(
      `AI 提炼出 ${candidates.length} 条候选需求，是否确认落库为草稿？`
    );
    if (confirm) {
      await apiFetch(`/notes/${noteId}/confirm-requirements`, {
        method: "POST",
        body: JSON.stringify({ candidates }),
      });
      alert("已生成需求草稿，可在「需求」页查看");
    }
  }

  const parse = (v: any) => {
    if (Array.isArray(v)) return v;
    if (typeof v === "string" && v) {
      try { return JSON.parse(v); } catch { return []; }
    }
    return [];
  };

  return (
    <Layout>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 }}>
        <h2 style={{ margin: 0, fontSize: 26, color: "#fff" }}>笔记</h2>
      </div>

      {notes.length === 0 && (
        <div className="gate-card"><p className="gate-muted" style={{ margin: 0 }}>暂无笔记。录音转写后自动生成。</p></div>
      )}

      {notes.map((n) => {
        const points = parse(n.points);
        const decisions = parse(n.decisions);
        const todos = parse(n.todos);
        const hasBody = (n.summary || points.length || decisions.length || todos.length);
        return (
          <div className="gate-card" key={n.id}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "start", gap: 12 }}>
              <div>
                <span className="gate-tag">{SCENE_LABEL[n.scene] ?? n.scene}</span>
                <h3 style={{ margin: "8px 0 0" }}>{n.summary || "（未生成摘要）"}</h3>
              </div>
              {hasBody && (
                <button
                  className="gate-btn gate-btn-ghost"
                  onClick={() => speak(`/notes/${n.id}/tts`)}
                  disabled={loading}
                >
                  {loading ? "合成中…" : "🔊 朗读"}
                </button>
              )}
            </div>

            {points.length > 0 && (
              <div style={{ marginTop: 10 }}>
                <p className="gate-muted" style={{ margin: "0 0 4px" }}>要点</p>
                {points.map((p: any, i: number) => (
                  <p key={i} style={{ margin: "2px 0", color: "#c9d1d9", fontSize: 14 }}>
                    · {p?.topic ? `[${p.topic}] ` : ""}{p?.detail ?? p}
                  </p>
                ))}
              </div>
            )}
            {decisions.length > 0 && (
              <div style={{ marginTop: 8 }}>
                <p className="gate-muted" style={{ margin: "0 0 4px" }}>决策</p>
                {decisions.map((d: any, i: number) => (
                  <p key={i} style={{ margin: "2px 0", color: "#34d399", fontSize: 14 }}>• {d?.content ?? d}</p>
                ))}
              </div>
            )}
            {todos.length > 0 && (
              <div style={{ marginTop: 8 }}>
                <p className="gate-muted" style={{ margin: "0 0 4px" }}>待办</p>
                {todos.map((t: any, i: number) => (
                  <p key={i} style={{ margin: "2px 0", color: "#7ea8f7", fontSize: 14 }}>
                    ☐ {t?.owner ? `[${t.owner}]` : ""}{t?.item ?? t}
                  </p>
                ))}
              </div>
            )}

            {n.scene === "discussion" && (
              <div style={{ marginTop: 14 }}>
                <button className="gate-btn" onClick={() => extract(n.id)}>提炼候选需求</button>
              </div>
            )}
          </div>
        );
      })}
    </Layout>
  );
}
