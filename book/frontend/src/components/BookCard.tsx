
import React from "react";
import { Book } from "../types";
import "./../App.css";

export const BookCard: React.FC<{
  book: Book;
  onDetails?: (b: Book) => void;
  onAdd?: (b: Book) => void;
  onFavorite?: (b: Book) => void;
}> = ({ book, onDetails, onAdd, onFavorite }) => {
  const avg = book.rating ?? 0;

  return (
    <div className="card">
      <div className="card-header">
        <div className="card-title">
          {book.title} {book.isDefault ? "✨" : ""}
        </div>
        <div className="card-badges">
          {book.genre && <span className="badge">🎨 {book.genre}</span>}
          {book.mood && <span className="badge">😊 {book.mood}</span>}
          {book.category && <span className="badge">🏷️ {book.category}</span>}
          <span className="badge">⭐ {avg.toFixed(1)}</span>
        </div>
      </div>
      <p className="muted">{book.author || "Unknown author"}</p>

      <div style={{ display: "flex", gap: ".5rem", flexWrap: "wrap" }}>
        {onDetails && <button className="btn btn-soft" onClick={() => onDetails(book)}>🔎 Details</button>}
        {onAdd && <button className="btn btn-primary" onClick={() => onAdd(book)}>📖 Add to List</button>}
        {onFavorite && <button className="btn btn-outline" onClick={() => onFavorite(book)}>💖 Favorite</button>}
      </div>
    </div>
  );
};
