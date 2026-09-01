import { useEffect, useState } from "react";
import Layout from "../components/Layout";
import { apiFetch } from "../api/client";
import { useAuth } from "../context/AuthContext";

const NEXT: Record<string, { label: string; to: string; role?: string }[]> = {
  draft: [{ label: "提交评审", to: "pending_review" }],
  pending_review: [
    { label: "可行", to: "feasible", role: "tech" },
    { label: "信息待补充", to: "info_needed", role: "tech" },
    { label: "方案待调整", to: "plan_needed", role: "tech" },
    { label: "不可行", to: "infeasible", role: "tech" },
  ],
  info_needed: [{ label: "重新提交评审", to: "pending_review" }],
  plan_needed: [{ label: "重新提交评审", to: "pending_review" }],
  infeasible: [{ label: "重新评估", to: "pending_review", role: "tech" }],
  feasible: [{ label: "开始开发", to: "in_dev", role: "tech" }],
  in_dev: [{ label: "标记交付", to: "delivered", role: "tech" }],
};

const STATUS_META: Record<string, { label: string; cls: string }> = {
  draft: { label: "草稿", cls: "gate-status-gray" },
  pending_review: { label: "待评审", cls: "gate-status-blue" },
  feasible: { label: "可行", cls: "gate-status-green" },
  in_dev: { label: "开发中", cls: "gate-status-blue" },
  delivered: { label: "已交付", cls: "gate-status-green" },
  info_needed: { label: "信息待补充", cls: "gate-status-gray" },
  plan_needed: { label: "方案待调整", cls: "gate-status-gray" },
  infeasible: { label: "不可行", cls: "gate-status-red" },
};

export default function Requirements() {
  const { role } = useAuth();
  const [items, setItems] = useState<any[]>([]);

  async function load() {
    setItems(await apiFetch("/requirements/"));
  }
  useEffect(() => {
    load();
  }, []);

  async function add() {
    const title = prompt("需求标题");
    if (!title) return;
    const description = prompt("需求描述") || "";
    await apiFetch("/requirements/", {
      method: "POST",
      body: JSON.stringify({ title, description, source: "manual" }),
    });
    load();
  }

  async function transition(id: number, to: string) {
    await apiFetch(`/requirements/${id}/transition`, {
      method: "POST",
      body: JSON.stringify({ to }),
    });
    load();
  }

  const canTransition = role === "tech" || role === "admin";

  return (
    <Layout>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 }}>
        <h2 style={{ margin: 0, fontSize: 26, color: "#fff" }}>需求</h2>
        <button className="gate-btn" onClick={add}>+ 新增需求</button>
      </div>

      {items.length === 0 && (
        <div className="gate-card"><p className="gate-muted" style={{ margin: 0 }}>暂无需求。从录音笔记提炼或手动录入。</p></div>
      )}

      {items.map((r) => {
        const meta = STATUS_META[r.status] ?? { label: r.status, cls: "gate-status-gray" };
        const actions = (NEXT[r.status] ?? []).filter((a) => !a.role || canTransition);
        return (
          <div className="gate-card" key={r.id}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "start", gap: 12 }}>
              <div>
                <h3 style={{ margin: 0 }}>{r.title}</h3>
                <p className="gate-muted" style={{ margin: "6px 0 0" }}>
                  {r.description || "（无描述）"}
                  {r.source_ref && <span className="gate-tag">来源</span>}
                </p>
              </div>
              <span className={meta.cls}>{meta.label}</span>
            </div>
            {actions.length > 0 && (
              <div style={{ display: "flex", gap: 8, marginTop: 14 }}>
                {actions.map((a) => (
                  <button key={a.to} className="gate-btn gate-btn-ghost" onClick={() => transition(r.id, a.to)}>
                    {a.label}
                  </button>
                ))}
              </div>
            )}
          </div>
        );
      })}
    </Layout>
  );
}
