import { useEffect, useState } from "react";
import { apiFetch } from "../api/client";

export default function Projects() {
  const [projects, setProjects] = useState<any[]>([]);
  async function load() {
    setProjects(await apiFetch("/projects/"));
  }
  useEffect(() => {
    load();
  }, []);
  async function addCustomer() {
    const name = prompt("客户名称");
    if (!name) return;
    await apiFetch("/customers/", { method: "POST", body: JSON.stringify({ name }) });
    alert("客户已创建");
  }
  async function addProject() {
    const name = prompt("项目名称");
    if (!name) return;
    const customer_id = Number(prompt("客户ID"));
    await apiFetch("/projects/", { method: "POST", body: JSON.stringify({ name, customer_id }) });
    load();
  }
  return (
    <div style={{ padding: 40 }}>
      <h2>项目</h2>
      <button onClick={addCustomer}>新建客户</button>
      <button onClick={addProject}>新建项目</button>
      <ul>
        {projects.map((p) => (
          <li key={p.id}>
            {p.name}（状态：{p.status}）
          </li>
        ))}
      </ul>
    </div>
  );
}
