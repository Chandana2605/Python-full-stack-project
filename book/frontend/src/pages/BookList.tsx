
import React, { useEffect, useMemo, useState } from "react";
import { api } from "../api";
import { useAuth } from "../authContext";
import { Book } from "../types";
import { BookCard } from "../components/BookCard";
import { FilterBar, Filters } from "../components/FilterBar";
import "./../App.css";

export const BookList: React.FC<{
  onDetails: (b: Book) => void;
}> = ({ onDetails }) => {
  const { token, role } = useAuth();
  const [books, setBooks] = useState<Book[]>([]);
  const [filters, setFilters] = useState<Filters>({
    q: "", genre: "", mood: "", category: "", minRating: 0
  });

  useEffect(() => {
    api.getBooks(token || undefined).then((res: any) => {
      setBooks(res?.books || res || []); // compatible either way
    }).catch(console.error);
  }, [token]);

  const filtered = useMemo(() => {
    const q = filters.q.trim().toLowerCase();
    return books.filter(b => {
      const matchesQ =
        !q ||
        (b.title?.toLowerCase().includes(q)) ||
        (b.author?.toLowerCase().includes(q));
      const matchesGenre = !filters.genre || b.genre === filters.genre;
      const matchesMood = !filters.mood || b.mood === filters.mood;
      const matchesCat = !filters.category || b.category === filters.category;
      const matchesRating = (b.rating ?? 0) >= filters.minRating;
      const isApproved = b.status !== 'rejected';
      return matchesQ && matchesGenre && matchesMood && matchesCat && matchesRating && isApproved;
    });
  }, [books, filters]);

  const handleAdd = (book: Book) => {
    if (!token) return alert("Please login first 😊");
    api.addBookToUserList(token, { book_id: book.id, status: "currently_reading" })
      .then(() => alert("Added to your list! 📚"))
      .catch(e => alert(String(e)));
  };

  const handleFav = (book: Book) => {
    alert(`Marked "${book.title}" as favorite 💖`);
    // Usually you'd call a favorite endpoint; keeping simple as requested.
  };

  return (
    <div className="container">
      <h2>🔍 Explore Books</h2>
      <p className="muted">Filter by genre, mood, category, rating, or search text.</p>

      <FilterBar filters={filters} setFilters={setFilters} />

      <div className="spacer"></div>

      <div className="grid">
        {filtered.map(b => (
          <BookCard
            key={b.id}
            book={b}
            onDetails={onDetails}
            onAdd={handleAdd}
            onFavorite={handleFav}
          />
        ))}
      </div>

      {!filtered.length && (
        <div className="section">
          <p>No books match your filters. Try clearing some filters 🧹</p>
        </div>
      )}
    </div>
  );
};
