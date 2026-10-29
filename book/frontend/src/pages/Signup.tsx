
// Signup.tsx
import React, { useState } from "react";
import { api } from "../api";
import "./../App.css";

export const Signup: React.FC = () => {
  const [name, setName] = useState(""); const [email, setEmail] = useState("");
  const [password, setPassword] = useState(""); const [isAdmin, setIsAdmin] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const res = isAdmin
        ? await api.adminSignup(name, email, password)
        : await api.signup(name, email, password);
      alert(`${res?.message || "Signup successful"} 🎉`);
    } catch (err) {
      alert(String(err));
    }
  };

  return (
    <div className="container">
      <form className="section" onSubmit={submit}>
        <h2>✍️ Signup</h2>
        <label className="muted">Name</label>
        <input className="input" value={name} onChange={e => setName(e.target.value)} />
        <div className="spacer"></div>
        <label className="muted">Email</label>
        <input className="input" value={email} onChange={e => setEmail(e.target.value)} />
        <div className="spacer"></div>
        <label className="muted">Password</label>
        <input className="input" type="password" value={password} onChange={e => setPassword(e.target.value)} />
        <div className="spacer"></div>
        <label className="muted">Account type</label>
        <select className="select" value={isAdmin ? "admin" : "user"} onChange={e => setIsAdmin(e.target.value === "admin")}>
          <option value="user">User</option>
          <option value="admin">Admin</option>
        </select>
        <div className="spacer"></div>
        <button className="btn btn-primary" type="submit">Create account</button>
      </form>
    </div>
  );
};
