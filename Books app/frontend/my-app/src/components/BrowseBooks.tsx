import React, { useState, useEffect } from 'react';
import { bookAPI } from '../services/api';
import { Book } from '../types';
import BookCard from './BookCard';
import './BrowseBooks.css';

interface BrowseBooksProps {
  onSelectBook: (book: Book) => void;
  onAddToList: (bookId: number, status: string) => void;
}

const BrowseBooks: React.FC<BrowseBooksProps> = ({ onSelectBook, onAddToList }) => {
  const [books, setBooks] = useState<Book[]>([]);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState({
    genre: '',
    mood: '',
    category: '',
    min_rating: ''
  });
  const [searchQuery, setSearchQuery] = useState('');

  useEffect(() => {
    loadBooks();
  }, [filters]);

  const loadBooks = async () => {
    try {
      const filterParams: any = {};
      if (filters.genre) filterParams.genre = filters.genre;
      if (filters.mood) filterParams.mood = filters.mood;
      if (filters.category) filterParams.category = filters.category;
      if (filters.min_rating) filterParams.min_rating = parseFloat(filters.min_rating);

      const response = await bookAPI.getBooks(filterParams);
      setBooks(response.data);
    } catch (err) {
      console.error('Failed to load books:', err);
    } finally {
      setLoading(false);
    }
  };

  const filteredBooks = books.filter(book =>
    book.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
    book.author_name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const genres = ['Fantasy', 'Science Fiction', 'Mystery', 'Romance', 'Thriller', 'Self-Help', 'Biography'];
  const moods = ['Magical', 'Exciting', 'Inspiring', 'Dark', 'Uplifting', 'Thought-provoking'];
  const categories = ['Fiction', 'Non-Fiction'];

  return (
    <div className="browse-books">
      <div className="browse-header">
        <h1>Discover Books 📚</h1>
        <p>Find your next great read</p>
      </div>

      <div className="search-bar">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <circle cx="11" cy="11" r="8" />
          <path d="m21 21-4.35-4.35" />
        </svg>
        <input
          type="text"
          placeholder="Search by title or author..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
        />
      </div>

      <div className="filters-container">
        <div className="filter-group">
          <label>Genre</label>
          <select
            value={filters.genre}
            onChange={(e) => setFilters({ ...filters, genre: e.target.value })}
          >
            <option value="">All Genres</option>
            {genres.map(genre => (
              <option key={genre} value={genre}>{genre}</option>
            ))}
          </select>
        </div>

        <div className="filter-group">
          <label>Mood</label>
          <select
            value={filters.mood}
            onChange={(e) => setFilters({ ...filters, mood: e.target.value })}
          >
            <option value="">All Moods</option>
            {moods.map(mood => (
              <option key={mood} value={mood}>{mood}</option>
            ))}
          </select>
        </div>

        <div className="filter-group">
          <label>Category</label>
          <select
            value={filters.category}
            onChange={(e) => setFilters({ ...filters, category: e.target.value })}
          >
            <option value="">All Categories</option>
            {categories.map(category => (
              <option key={category} value={category}>{category}</option>
            ))}
          </select>
        </div>

        <div className="filter-group">
          <label>Min Rating</label>
          <select
            value={filters.min_rating}
            onChange={(e) => setFilters({ ...filters, min_rating: e.target.value })}
          >
            <option value="">Any Rating</option>
            <option value="4">4+ Stars</option>
            <option value="3">3+ Stars</option>
            <option value="2">2+ Stars</option>
          </select>
        </div>

        <button
          className="clear-filters"
          onClick={() => setFilters({ genre: '', mood: '', category: '', min_rating: '' })}
        >
          Clear Filters
        </button>
      </div>

      {loading ? (
        <div className="loading-state">
          <div className="spinner"></div>
          <p>Loading books...</p>
        </div>
      ) : filteredBooks.length === 0 ? (
        <div className="empty-state">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
            <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
          </svg>
          <h3>No books found</h3>
          <p>Try adjusting your filters or search query</p>
        </div>
      ) : (
        <div className="books-grid">
          {filteredBooks.map(book => (
            <BookCard
              key={book.id}
              book={book}
              onSelect={() => onSelectBook(book)}
            />
          ))}
        </div>
      )}
    </div>
  );
};

export default BrowseBooks;