import { useEffect, useState } from "react";
import Layout from "../components/Layout";
import { apiFetch } from "../api/client";
import { useAuth } from "../context/AuthContext";

export default function Knowledge() {
  const { role } = useAuth();
  const [items, setItems] = useState<any[]>([]);

  async function load() {
    setItems(await apiFetch("/knowledge/"));
  }
  useEffect(() => {
    load();
  }, []);

  async function add() {
    const title = prompt("标题");
    const content = prompt("内容");
    if (!title || !content) return;
    await apiFetch("/knowledge/", { method: "POST", body: JSON.stringify({ title, content }) });
    load();
  }

  const canWrite = role === "tech" || role === "admin";

  return (
    <Layout>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 }}>
        <h2 style={{ margin: 0, fontSize: 26, color: "#fff" }}>知识库</h2>
        {canWrite && <button className="gate-btn" onClick={add}>+ 新建条目</button>}
      </div>

      {items.length === 0 && (
        <div className="gate-card"><p className="gate-muted" style={{ margin: 0 }}>暂无知识条目。手动导入或答疑回流。</p></div>
      )}

      {items.map((k) => (
        <div className="gate-card" key={k.id}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <h3 style={{ margin: 0 }}>{k.title}</h3>
            <span className="gate-tag">{k.source === "qa" ? "答疑回流" : "手动导入"}</span>
          </div>
          <p className="gate-muted" style={{ margin: "8px 0 0" }}>{k.content}</p>
        </div>
      ))}
    </Layout>
  );
}
