import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider, useAuth } from "./context/AuthContext";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import Projects from "./pages/Projects";
import Requirements from "./pages/Requirements";
import Knowledge from "./pages/Knowledge";
import Notes from "./pages/Notes";
import QA from "./pages/QA";

function Guard({ children }: { children: JSX.Element }) {
  const { token } = useAuth();
  return token ? children : <Navigate to="/login" />;
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/" element={<Guard><Dashboard /></Guard>} />
          <Route path="/projects" element={<Guard><Projects /></Guard>} />
          <Route path="/notes" element={<Guard><Notes /></Guard>} />
          <Route path="/requirements" element={<Guard><Requirements /></Guard>} />
          <Route path="/knowledge" element={<Guard><Knowledge /></Guard>} />
          <Route path="/qa" element={<Guard><QA /></Guard>} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
