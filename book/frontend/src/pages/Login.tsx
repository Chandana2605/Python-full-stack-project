
// Login.tsx
import React, { useState } from "react";
import { api } from "../api";
import { useAuth } from "../authContext";
import "./../App.css";

export const Login: React.FC = () => {
  const { setAuth } = useAuth();
  const [email, setEmail] = useState(""); const [password, setPassword] = useState("");
  const [isAdmin, setIsAdmin] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const res = isAdmin ? await api.adminLogin(email, password) : await api.login(email, password);
      setAuth(res.access_token, isAdmin ? "admin" : "user");
      alert("Logged in! 🎉");
    } catch (err) {
      alert(String(err));
    }
  };

  return (
    <div className="container">
      <form className="section" onSubmit={submit}>
        <h2>🔐 Login</h2>
        <label className="muted">Email</label>
        <input className="input" value={email} onChange={e => setEmail(e.target.value)} />
        <div className="spacer"></div>
        <label className="muted">Password</label>
        <input className="input" type="password" value={password} onChange={e => setPassword(e.target.value)} />
        <div className="spacer"></div>
        <label className="muted">Login as</label>
        <select className="select" value={isAdmin ? "admin" : "user"} onChange={e => setIsAdmin(e.target.value === "admin")}>
          <option value="user">User</option>
          <option value="admin">Admin</option>
        </select>
        <div className="spacer"></div>
        <button className="btn btn-primary" type="submit">Login</button>
      </form>
    </div>
  );
};
