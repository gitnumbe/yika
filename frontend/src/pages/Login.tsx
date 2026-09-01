import { useState, type FormEvent } from "react";
import { useAuth } from "../context/AuthContext";
import "./login.css";

/* GateAI 品牌 logo：Gate(白) + AI(蓝) + 蓝色四角星
   深色适配版，全部内联实现，无外部图片依赖 */
function GateAILogo({ size = 17 }: { size?: number }) {
  return (
    <span className="gateai-logo" style={{ fontSize: size }}>
      <svg
        width={size * 1.15}
        height={size * 1.15}
        viewBox="0 0 24 24"
        className="gateai-star"
        aria-hidden="true"
      >
        <path
          d="M12 2.4c.55 4.3 5 8.7 9.3 9.3-4.3.6-8.75 5-9.3 9.3-.55-4.3-5-8.7-9.3-9.3C7 11.1 11.45 6.7 12 2.4Z"
          fill="currentColor"
        />
      </svg>
      <span className="gateai-gate">Gate</span>
      <span className="gateai-ai">AI</span>
    </span>
  );
}

export default function Login() {
  const { login } = useAuth();
  const [u, setU] = useState("");
  const [p, setP] = useState("");
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(false);
  const [showPwd, setShowPwd] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (!u.trim() || !p) {
      setErr("请输入用户名和密码");
      return;
    }
    setLoading(true);
    setErr("");
    try {
      await login(u, p);
      window.location.href = "/";
    } catch {
      setErr("登录失败，请检查用户名密码");
      setLoading(false);
    }
  }

  return (
    <div className="login-page">
      <div className="login-card">
        {/* 左侧：视频 + 品牌 */}
        <div className="login-media">
          <video
            className="login-video"
            src="/login-video.mp4"
            autoPlay
            muted
            loop
            playsInline
          />
          <div className="login-media-overlay" />
          <div className="login-brand">
            <GateAILogo size={20} />
          </div>
          <div className="login-media-caption">AI 驱动的团队协作平台</div>
        </div>

        {/* 右侧：登录表单 */}
        <div className="login-form-side">
          <div className="login-form-inner">
            <p className="login-eyebrow">内部协作平台</p>
            <h2 className="login-title">欢迎回来</h2>
            <p className="login-subtitle">登录以继续协作</p>

            <form onSubmit={submit} className="login-form">
              <div className="login-field">
                <label className="login-label" htmlFor="username">
                  用户名
                </label>
                <input
                  id="username"
                  className="login-input"
                  placeholder="请输入用户名"
                  value={u}
                  onChange={(e) => setU(e.target.value)}
                  autoComplete="username"
                  autoFocus
                />
              </div>

              <div className="login-field">
                <label className="login-label" htmlFor="password">
                  密码
                </label>
                <div className="login-pwd-wrap">
                  <input
                    id="password"
                    className="login-input"
                    type={showPwd ? "text" : "password"}
                    placeholder="请输入密码"
                    value={p}
                    onChange={(e) => setP(e.target.value)}
                    autoComplete="current-password"
                  />
                  <button
                    type="button"
                    className="login-eye"
                    aria-label={showPwd ? "隐藏密码" : "显示密码"}
                    onClick={() => setShowPwd((s) => !s)}
                  >
                    {showPwd ? <EyeOffIcon /> : <EyeIcon />}
                  </button>
                </div>
              </div>

              {err && <p className="login-error">{err}</p>}

              <button className="login-submit" type="submit" disabled={loading}>
                {loading ? (
                  <>
                    <span className="login-spinner" />
                    登录中…
                  </>
                ) : (
                  "登 录"
                )}
              </button>
            </form>

            <p className="login-footer">账号由管理员开通 · 纯内部使用</p>
          </div>
        </div>
      </div>
    </div>
  );
}

function EyeIcon() {
  return (
    <svg
      width="18"
      height="18"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
      <circle cx="12" cy="12" r="3" />
    </svg>
  );
}

function EyeOffIcon() {
  return (
    <svg
      width="18"
      height="18"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24" />
      <line x1="1" y1="1" x2="23" y2="23" />
    </svg>
  );
}
