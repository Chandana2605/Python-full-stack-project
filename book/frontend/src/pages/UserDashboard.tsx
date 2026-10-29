
import React, { useEffect, useState } from "react";
import { api } from "../api";
import { useAuth } from "../authContext";
import { Book, UserDashboard } from "../types";
import { BookCard } from "../components/BookCard";
import "./../App.css";

export const UserDashboard: React.FC<{ onDetails: (b: Book) => void }> = ({ onDetails }) => {
  const { token } = useAuth();
  const [dash, setDash] = useState<UserDashboard | null>(null);

  useEffect(() => {
    if (!token) return;
    api.userDashboard(token).then(setDash).catch(console.error);
  }, [token]);

  if (!token) return <div className="container"><div className="section">Please login to see your dashboard.</div></div>;
  if (!dash) return <div className="container"><div className="section">Loading…</div></div>;

  return (
    <div className="container">
      <div className="section">
        <h2>🧑‍💻 My Dashboard</h2>
        <p>🔥 Streak: <strong>{dash.streak}</strong></p>
        {dash.favourite_genre && <p>⭐ Favourite genre: <strong>{dash.favourite_genre}</strong></p>}
      </div>

      <div className="spacer"></div>

      <h3>💖 Favorites</h3>
      <div className="grid">
        {(dash.favorites || []).map(b => (
          <BookCard key={b.id} book={b} onDetails={onDetails} />
        ))}
      </div>

      <div className="spacer"></div>

      <h3>📚 Currently Reading</h3>
      <div className="grid">
        {(dash.currently_reading || []).map(b => <BookCard key={b.id} book={b} onDetails={onDetails} />)}
      </div>

      <div className="spacer"></div>

      <h3>✅ Completed</h3>
      <div className="grid">
        {(dash.completed || []).map(b => <BookCard key={b.id} book={b} onDetails={onDetails} />)}
      </div>

      <div className="spacer"></div>

      <h3>🧾 Wish to Read</h3>
      <div className="grid">
        {(dash.wish_to_read || []).map(b => <BookCard key={b.id} book={b} onDetails={onDetails} />)}
      </div>

      <div className="spacer"></div>

      <h3>🧑‍🎨 My Posted Books</h3>
      <div className="grid">
        {(dash.posted_books || []).map(b => <BookCard key={b.id} book={b} onDetails={onDetails} />)}
      </div>
    </div>
  );
};
