
import React, { useEffect, useState } from "react";
import { api } from "../api";
import { useAuth } from "../authContext";
import { Book } from "../types";
import "./../App.css";

export const BookDetails: React.FC<{
  bookId: number | null;
}> = ({ bookId }) => {
  const { token } = useAuth();
  const [book, setBook] = useState<Book | null>(null);
  const [rating, setRating] = useState<number>(5);
  const [favorite, setFavorite] = useState<boolean>(false);
  const [recommended, setRecommended] = useState<boolean>(true);
  const [text, setText] = useState<string>("");

  useEffect(() => {
    if (!bookId) return;
    api.getBook(bookId, token || undefined).then(setBook).catch(console.error);
  }, [bookId, token]);

  if (!bookId) return <div className="container"><div className="section">Select a book to view details.</div></div>;
  if (!book) return <div className="container"><div className="section">Loading…</div></div>;

  const addTo = (status: string) => {
    if (!token) return alert("Login required 😊");
    api.addBookToUserList(token, { book_id: book.id, status })
      .then(() => alert(`Marked as ${status.replace('_', ' ')} ✅`))
      .catch(e => alert(String(e)));
  };

  const submitReview = () => {
    if (!token) return alert("Login required 😊");
    api.createReview(token, book.id, { rating, favorite, recommended, text })
      .then(() => alert("Review posted! 📝"))
      .catch(e => alert(String(e)));
  };

  return (
    <div className="container">
      <div className="section">
        <h2>📖 {book.title}</h2>
        <p className="muted">{book.author || "Unknown author"}</p>
        <div className="card-badges" style={{ marginTop: ".6rem" }}>
          {book.genre && <span className="badge">🎨 {book.genre}</span>}
          {book.mood && <span className="badge">😊 {book.mood}</span>}
          {book.category && <span className="badge">🏷️ {book.category}</span>}
          <span className="badge">⭐ {book.rating ?? 0}</span>
        </div>

        <div className="spacer"></div>

        <div style={{ display: "flex", gap: ".5rem", flexWrap: "wrap" }}>
          <button className="btn btn-primary" onClick={() => addTo("currently_reading")}>📚 Start Reading</button>
          <button className="btn btn-soft" onClick={() => addTo("wish_to_read")}>🧾 Wish to Read</button>
          <button className="btn btn-outline" onClick={() => addTo("completed")}>✅ Mark Completed</button>
        </div>

        <div className="spacer"></div>

        <h3>📝 Review</h3>
        <div style={{ display: "grid", gap: ".6rem", gridTemplateColumns: "1fr 1fr 1fr" }}>
          <div>
            <label className="muted">Rating (0 - 5)</label>
            <input className="input" type="number" min={0} max={5} step={0.5}
              value={rating} onChange={(e) => setRating(Number(e.target.value))} />
          </div>
          <div>
            <label className="muted">Favorite</label>
            <select className="select" value={favorite ? "yes" : "no"}
              onChange={(e) => setFavorite(e.target.value === "yes")}>
              <option value="no">No</option>
              <option value="yes">Yes 💖</option>
            </select>
          </div>
          <div>
            <label className="muted">Recommended</label>
            <select className="select" value={recommended ? "yes" : "no"}
              onChange={(e) => setRecommended(e.target.value === "yes")}>
              <option value="yes">Yes ✅</option>
              <option value="no">No ❌</option>
            </select>
          </div>
        </div>
        <div className="spacer"></div>
        <textarea className="textarea" placeholder="Share your thoughts… ✨"
          value={text} onChange={(e) => setText(e.target.value)} />
        <div className="spacer"></div>
        <button className="btn btn-primary" onClick={submitReview}>🚀 Submit Review</button>
      </div>
    </div>
  );
};
