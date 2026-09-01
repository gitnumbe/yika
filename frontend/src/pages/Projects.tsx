import { useEffect, useState } from "react";
import Layout from "../components/Layout";
import { apiFetch } from "../api/client";

const STATUS_LABEL: Record<string, string> = {
  prep: "筹备/学习",
  training: "培训中",
  exploration: "需求探索",
  review: "需求评审",
  dev: "开发中",
  delivered: "已交付",
};

export default function Projects() {
  const [projects, setProjects] = useState<any[]>([]);
  const [customers, setCustomers] = useState<any[]>([]);

  async function load() {
    setProjects(await apiFetch("/projects/"));
    setCustomers(await apiFetch("/customers/"));
  }
  useEffect(() => {
    load();
  }, []);

  async function addCustomer() {
    const name = prompt("客户名称");
    if (!name) return;
    await apiFetch("/customers/", { method: "POST", body: JSON.stringify({ name }) });
    load();
  }
  async function addProject() {
    const name = prompt("项目名称");
    if (!name) return;
    const customer_id = Number(prompt("客户ID（可从客户列表查看）"));
    if (!customer_id) return;
    await apiFetch("/projects/", { method: "POST", body: JSON.stringify({ name, customer_id }) });
    load();
  }

  return (
    <Layout>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 }}>
        <h2 style={{ margin: 0, fontSize: 26, color: "#fff" }}>项目</h2>
        <div style={{ display: "flex", gap: 10 }}>
          <button className="gate-btn gate-btn-ghost" onClick={addCustomer}>+ 客户</button>
          <button className="gate-btn" onClick={addProject}>+ 项目</button>
        </div>
      </div>

      <div className="gate-card">
        <h3>客户档案（{customers.length}）</h3>
        {customers.length === 0 && <p className="gate-muted">暂无客户，点击"客户"创建。</p>}
        {customers.map((c) => (
          <div className="gate-row" key={c.id}>
            <span><b style={{ color: "#fff" }}>{c.name}</b></span>
            <span className="gate-muted">ID {c.id}{c.industry ? ` · ${c.industry}` : ""}</span>
          </div>
        ))}
      </div>

      <div className="gate-card">
        <h3>项目列表（{projects.length}）</h3>
        {projects.length === 0 && <p className="gate-muted">暂无项目。</p>}
        {projects.map((p) => (
          <div className="gate-row" key={p.id}>
            <span><b style={{ color: "#fff" }}>{p.name}</b></span>
            <span className="gate-status gate-status-blue">{STATUS_LABEL[p.status] ?? p.status}</span>
          </div>
        ))}
      </div>
    </Layout>
  );
}
