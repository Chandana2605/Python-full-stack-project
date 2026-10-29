
import React, { useMemo } from "react";
import "./../App.css";

export interface Filters {
  q: string;
  genre: string;
  mood: string;
  category: string;
  minRating: number;
}

const GENRES = ["Fiction","Non-Fiction","Fantasy","Sci-Fi","Mystery","Romance","Horror","Biography","History","Self-Help"];
const MOODS = ["Happy","Sad","Thrilling","Calm","Inspirational","Dark","Whimsical"];
const CATS  = ["Classic","Modern","Young Adult","Children","Poetry","Comics","Philosophy"];

export const FilterBar: React.FC<{
  filters: Filters;
  setFilters: (f: Filters) => void;
  onApply?: () => void; // optional call to backend with params if supported
}> = ({ filters, setFilters, onApply }) => {
  const debouncedApply = useMemo(() => {
    let t: any;
    return () => { clearTimeout(t); t = setTimeout(() => onApply && onApply(), 250); };
  }, [onApply]);

  return (
    <div className="section">
      <div className="filter">
        <div>
          <label className="muted">Search</label>
          <input
            className="input"
            placeholder="🔎 title, author..."
            value={filters.q}
            onChange={(e) => { setFilters({ ...filters, q: e.target.value }); debouncedApply(); }}
          />
        </div>
        <div>
          <label className="muted">Genre</label>
          <select
            className="select"
            value={filters.genre}
            onChange={(e) => { setFilters({ ...filters, genre: e.target.value }); onApply && onApply(); }}
          >
            <option value="">Any</option>
            {GENRES.map(g => <option key={g} value={g}>{g}</option>)}
          </select>
        </div>
        <div>
          <label className="muted">Mood</label>
          <select
            className="select"
            value={filters.mood}
            onChange={(e) => { setFilters({ ...filters, mood: e.target.value }); onApply && onApply(); }}
          >
            <option value="">Any</option>
            {MOODS.map(m => <option key={m} value={m}>{m}</option>)}
          </select>
        </div>
        <div>
          <label className="muted">Category</label>
          <select
            className="select"
            value={filters.category}
            onChange={(e) => { setFilters({ ...filters, category: e.target.value }); onApply && onApply(); }}
          >
            <option value="">Any</option>
            {CATS.map(c => <option key={c} value={c}>{c}</option>)}
          </select>
        </div>
        <div>
          <label className="muted">Min ⭐</label>
          <input
            className="input"
            type="number" min={0} max={5} step={0.5}
            value={filters.minRating}
            onChange={(e) => { setFilters({ ...filters, minRating: Number(e.target.value) }); onApply && onApply(); }}
          />
        </div>
      </div>
    </div>
  );
};
