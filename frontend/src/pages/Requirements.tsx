import { useEffect, useState } from "react";
import { apiFetch } from "../api/client";
import { useAuth } from "../context/AuthContext";

const NEXT: Record<string, { label: string; to: string }[]> = {
  draft: [{ label: "提交评审", to: "pending_review" }],
  pending_review: [
    { label: "可行", to: "feasible" },
    { label: "信息待补充", to: "info_needed" },
    { label: "方案待调整", to: "plan_needed" },
    { label: "不可行", to: "infeasible" },
  ],
  info_needed: [{ label: "重新提交评审", to: "pending_review" }],
  plan_needed: [{ label: "重新提交评审", to: "pending_review" }],
  infeasible: [{ label: "重新评估", to: "pending_review" }],
  feasible: [{ label: "开始开发", to: "in_dev" }],
  in_dev: [{ label: "标记交付", to: "delivered" }],
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
    await apiFetch("/requirements/", { method: "POST", body: JSON.stringify({ title }) });
    load();
  }
  async function transition(id: number, to: string) {
    await apiFetch(`/requirements/${id}/transition`, { method: "POST", body: JSON.stringify({ to }) });
    load();
  }
  return (
    <div style={{ padding: 40 }}>
      <h2>需求</h2>
      <button onClick={add}>新建需求</button>
      <ul>
        {items.map((r) => (
          <li key={r.id}>
            {r.title}（{r.status}）{" "}
            {(role === "tech" || role === "admin") &&
              (NEXT[r.status] || []).map((a) => (
                <button key={a.to} onClick={() => transition(r.id, a.to)}>
                  {a.label}
                </button>
              ))}
          </li>
        ))}
      </ul>
    </div>
  );
}
