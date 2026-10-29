
import React, { useEffect, useState } from "react";
import { api } from "../api";
import { useAuth } from "../authContext";
import { Book } from "../types";
import { BookCard } from "../components/BookCard";
import "./../App.css";

export const AdminDashboard: React.FC<{ onDetails: (b: Book) => void }> = ({ onDetails }) => {
  const { token, role } = useAuth();
  const [pending, setPending] = useState<Book[]>([]);
  const [all, setAll] = useState<Book[]>([]);
  const [title, setTitle] = useState("");
  const [genre, setGenre] = useState("");

  const load = () => {
    if (!token) return;
    api.adminPending(token).then((res: any) => setPending(res?.books || res || [])).catch(console.error);
    api.adminAllBooks(token).then((res: any) => setAll(res?.books || res || [])).catch(console.error);
  };

  useEffect(() => { load(); }, [token]);

  if (role !== "admin") return <div className="container"><div className="section">Admin only.</div></div>;

  const addDefault = () => {
    if (!token) return;
    api.adminAddDefaultBook(token, { title, genre, isDefault: true })
      .then(() => { setTitle(""); setGenre(""); load(); })
      .catch(e => alert(String(e)));
  };

  const approve = (b: Book, yes: boolean) => {
    const reason = yes ? undefined : prompt("Reason for rejecting:");
    if (!token) return;
    api.adminApproveReject(token, b.id, yes, reason)
      .then(load).catch(e => alert(String(e)));
  };

  const removeBook = (b: Book) => {
    if (!token) return;
    if (!confirm(`Delete "${b.title}"?`)) return;
    api.adminDeleteBook(token, b.id).then(load).catch(e => alert(String(e)));
  };

  return (
    <div className="container">
      <div className="section">
        <h2>🛠️ Admin Dashboard</h2>
        <p className="muted">Approve or reject user-posted books, manage defaults, and view all books.</p>
      </div>

      <div className="spacer"></div>

      <div className="section">
        <h3>✨ Add Default Book</h3>
        <div style={{ display: "grid", gap: ".6rem", gridTemplateColumns: "1fr 200px 160px" }}>
          <input className="input" placeholder="Title" value={title} onChange={e => setTitle(e.target.value)} />
          <input className="input" placeholder="Genre" value={genre} onChange={e => setGenre(e.target.value)} />
          <button className="btn btn-primary" onClick={addDefault}>Add</button>
        </div>
      </div>

      <div className="spacer"></div>

      <h3>⏳ Pending Approval</h3>
      <div className="grid">
        {pending.map(b => (
          <div key={b.id} className="card">
            <BookCard book={b} onDetails={onDetails} />
            <div style={{ display: "flex", gap: ".5rem", marginTop: ".5rem" }}>
              <button className="btn btn-primary" onClick={() => approve(b, true)}>✅ Approve</button>
              <button className="btn btn-outline" onClick={() => approve(b, false)}>❌ Reject</button>
            </div>
          </div>
        ))}
      </div>

      <div className="spacer"></div>

      <h3>📚 All Books</h3>
      <div className="grid">
        {all.map(b => (
          <div key={b.id} className="card">
            <BookCard book={b} onDetails={onDetails} />
            <div style={{ display: "flex", gap: ".5rem", marginTop: ".5rem" }}>
              <button className="btn btn-outline" onClick={() => removeBook(b)}>🗑️ Delete</button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
