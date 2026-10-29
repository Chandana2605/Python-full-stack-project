import React, { useState, useEffect } from 'react';
import { dashboardAPI, bookAPI, userBookAPI } from '../services/api';
import { Dashboard, Book } from '../types';
import BookCard from './BookCard';
import BookReader from './BookReader';
import BrowseBooks from './BrowseBooks';
import AddBook from './AddBook';
import './UserDashboard.css';

interface UserDashboardProps {
  username: string;
  onLogout: () => void;
}

const UserDashboard: React.FC<UserDashboardProps> = ({ username, onLogout }) => {
  const [activeTab, setActiveTab] = useState('home');
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [selectedBook, setSelectedBook] = useState<Book | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadDashboard();
  }, []);

  const loadDashboard = async () => {
    try {
      const response = await dashboardAPI.getUserDashboard();
      setDashboard(response.data);
    } catch (err) {
      console.error('Failed to load dashboard:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleAddToList = async (bookId: number, status: string) => {
    try {
      await userBookAPI.addBook(bookId, status);
      loadDashboard();
    } catch (err) {
      console.error('Failed to add book:', err);
    }
  };

  if (selectedBook) {
    return (
      <BookReader
        book={selectedBook}
        onClose={() => {
          setSelectedBook(null);
          loadDashboard();
        }}
      />
    );
  }

  return (
    <div className="user-dashboard">
      <div className="dashboard-sidebar">
        <div className="sidebar-header">
          <div className="logo">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
              <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
            </svg>
            <span>BookFinder</span>
          </div>
          
          <div className="user-info">
            <div className="user-avatar">{username.charAt(0).toUpperCase()}</div>
            <div className="user-details">
              <div className="user-name">{username}</div>
              <div className="user-streak">
                <svg viewBox="0 0 24 24" fill="currentColor">
                  <path d="M12 2C12 2 7 8 7 12C7 15.31 9.69 18 13 18C16.31 18 19 15.31 19 12C19 8 14 2 14 2H12ZM13 16C10.79 16 9 14.21 9 12C9 10.54 10.08 8.66 11.5 6.5C12 7.15 12.5 7.85 13 8.6C13.88 9.86 15 11.5 15 12C15 14.21 13.21 16 13 16Z"/>
                </svg>
                <span>{dashboard?.streak || 0} day streak</span>
              </div>
            </div>
          </div>
        </div>

        <nav className="sidebar-nav">
          <button
            className={activeTab === 'home' ? 'nav-item active' : 'nav-item'}
            onClick={() => setActiveTab('home')}
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
              <polyline points="9 22 9 12 15 12 15 22" />
            </svg>
            <span>Home</span>
          </button>

          <button
            className={activeTab === 'browse' ? 'nav-item active' : 'nav-item'}
            onClick={() => setActiveTab('browse')}
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="11" cy="11" r="8" />
              <path d="m21 21-4.35-4.35" />
            </svg>
            <span>Browse Books</span>
          </button>

          <button
            className={activeTab === 'add' ? 'nav-item active' : 'nav-item'}
            onClick={() => setActiveTab('add')}
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="12" y1="5" x2="12" y2="19" />
              <line x1="5" y1="12" x2="19" y2="12" />
            </svg>
            <span>Add Book</span>
          </button>

          <button className="nav-item logout" onClick={onLogout}>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
              <polyline points="16 17 21 12 16 7" />
              <line x1="21" y1="12" x2="9" y2="12" />
            </svg>
            <span>Logout</span>
          </button>
        </nav>
      </div>

      <div className="dashboard-content">
        {activeTab === 'home' && dashboard && (
          <div className="home-content">
            <div className="content-header">
              <h1>Welcome back, {username}! 👋</h1>
              <p>Continue your reading journey</p>
            </div>

            {dashboard.currently_reading.length > 0 && (
              <section className="book-section">
                <h2>📖 Currently Reading</h2>
                <div className="book-grid">
                  {dashboard.currently_reading.map(book => (
                    <BookCard
                      key={book.id}
                      book={book}
                      onSelect={() => setSelectedBook(book)}
                    />
                  ))}
                </div>
              </section>
            )}

            {dashboard.favorites.length > 0 && (
              <section className="book-section">
                <h2>❤️ Your Favorites</h2>
                <div className="book-grid">
                  {dashboard.favorites.map(book => (
                    <BookCard
                      key={book.id}
                      book={book}
                      onSelect={() => setSelectedBook(book)}
                      isFavorite
                    />
                  ))}
                </div>
              </section>
            )}

            {dashboard.wish_to_read.length > 0 && (
              <section className="book-section">
                <h2>📚 Want to Read</h2>
                <div className="book-grid">
                  {dashboard.wish_to_read.map(book => (
                    <BookCard
                      key={book.id}
                      book={book}
                      onSelect={() => setSelectedBook(book)}
                    />
                  ))}
                </div>
              </section>
            )}

            {dashboard.completed.length > 0 && (
              <section className="book-section">
                <h2>✅ Completed</h2>
                <div className="book-grid">
                  {dashboard.completed.map(book => (
                    <BookCard
                      key={book.id}
                      book={book}
                      onSelect={() => setSelectedBook(book)}
                    />
                  ))}
                </div>
              </section>
            )}

            {dashboard.posted_books.length > 0 && (
              <section className="book-section">
                <h2>✍️ Your Books</h2>
                <div className="book-grid">
                  {dashboard.posted_books.map(book => (
                    <BookCard
                      key={book.id}
                      book={book}
                      onSelect={() => setSelectedBook(book)}
                      showStatus
                    />
                  ))}
                </div>
              </section>
            )}
          </div>
        )}

        {activeTab === 'browse' && (
          <BrowseBooks
            onSelectBook={setSelectedBook}
            onAddToList={handleAddToList}
          />
        )}

        {activeTab === 'add' && (
          <AddBook onSuccess={loadDashboard} />
        )}
      </div>
    </div>
  );
};

export default UserDashboard;