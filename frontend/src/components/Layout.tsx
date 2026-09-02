import { Link, NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

/** GateAILogo 复用（与 Login 同源，内联 SVG 四角星） */
function Logo() {
  return (
    <span className="gate-brand">
      <svg className="star" width="17" height="17" viewBox="0 0 24 24" aria-hidden="true">
        <path
          d="M12 2.4c.55 4.3 5 8.7 9.3 9.3-4.3.6-8.75 5-9.3 9.3-.55-4.3-5-8.7-9.3-9.3C7 11.1 11.45 6.7 12 2.4Z"
          fill="currentColor"
        />
      </svg>
      Gate<span style={{ color: "var(--gate-blue)" }}>AI</span>
    </span>
  );
}

export default function Layout({ children }: { children: React.ReactNode }) {
  const { role, logout } = useAuth();
  const nav = useNavigate();
  return (
    <div className="gate-shell">
      <div className="gate-topbar">
        <Link to="/" style={{ textDecoration: "none" }}>
          <Logo />
        </Link>
        <nav className="gate-nav">
          <NavLink to="/" end>工作台</NavLink>
          <NavLink to="/projects">项目</NavLink>
          <NavLink to="/notes">笔记</NavLink>
          <NavLink to="/requirements">需求</NavLink>
          <NavLink to="/knowledge">知识库</NavLink>
          <NavLink to="/qa">答疑</NavLink>
        </nav>
        <div className="gate-user">
          <span className="gate-tag">{role}</span>
          <button
            className="gate-btn gate-btn-ghost"
            onClick={() => { logout(); nav("/login"); }}
          >
            退出登录
          </button>
        </div>
      </div>
      <main>{children}</main>
    </div>
  );
}
