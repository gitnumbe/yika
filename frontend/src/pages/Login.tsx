import { useState } from "react";
import { useAuth } from "../context/AuthContext";

export default function Login() {
  const { login } = useAuth();
  const [u, setU] = useState("");
  const [p, setP] = useState("");
  const [err, setErr] = useState("");
  async function submit() {
    try {
      await login(u, p);
      window.location.href = "/";
    } catch (e) {
      setErr("登录失败，请检查用户名密码");
    }
  }
  return (
    <div style={{ padding: 40 }}>
      <h2>登录</h2>
      <div>
        <input placeholder="用户名" value={u} onChange={(e) => setU(e.target.value)} />
      </div>
      <div>
        <input placeholder="密码" type="password" value={p} onChange={(e) => setP(e.target.value)} />
      </div>
      {err && <p style={{ color: "red" }}>{err}</p>}
      <button onClick={submit}>登录</button>
    </div>
  );
}
