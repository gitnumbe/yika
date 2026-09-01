import { Link } from "react-router-dom";
import Layout from "../components/Layout";
import { useAuth } from "../context/AuthContext";

const STATS = [
  { to: "/projects", label: "项目", desc: "客户项目跟进" },
  { to: "/requirements", label: "需求", desc: "评审与交付流转" },
  { to: "/knowledge", label: "知识库", desc: "团队知识沉淀" },
  { to: "/qa", label: "答疑", desc: "讲师问答飞轮" },
];

export default function Dashboard() {
  const { role } = useAuth();
  return (
    <Layout>
      <h2 style={{ margin: "0 0 8px", fontSize: 26, color: "#fff" }}>工作台</h2>
      <p className="gate-muted" style={{ marginBottom: 28 }}>
        你好，当前角色：<b style={{ color: "#fff" }}>{role}</b>。这里是组内协作的主入口。
      </p>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: 16 }}>
        {STATS.map((s) => (
          <Link key={s.to} to={s.to} style={{ textDecoration: "none" }}>
            <div className="gate-card" style={{ cursor: "pointer" }}>
              <h3>{s.label}</h3>
              <p className="gate-muted" style={{ margin: 0 }}>{s.desc}</p>
            </div>
          </Link>
        ))}
      </div>
    </Layout>
  );
}
