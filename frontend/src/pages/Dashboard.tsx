import { Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function Dashboard() {
  const { role, logout } = useAuth();
  return (
    <div style={{ padding: 40 }}>
      <h2>工作台</h2>
      <p>当前角色：{role}</p>
      <nav>
        <Link to="/projects">项目</Link> | <Link to="/requirements">需求</Link> |{" "}
        <Link to="/knowledge">知识库</Link> | <Link to="/qa">答疑</Link>
      </nav>
      <p>
        <button onClick={logout}>退出登录</button>
      </p>
    </div>
  );
}
