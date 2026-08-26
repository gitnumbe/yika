import { useEffect, useState } from "react";
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
  return (
    <div style={{ padding: 40 }}>
      <h2>知识库</h2>
      {(role === "tech" || role === "admin") && <button onClick={add}>新建知识条目</button>}
      <ul>
        {items.map((k) => (
          <li key={k.id}>{k.title}</li>
        ))}
      </ul>
    </div>
  );
}
