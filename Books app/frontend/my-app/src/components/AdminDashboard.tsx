import React, { useState, useEffect } from 'react';
import { adminAPI, dashboardAPI } from '../services/api';
import { Book, AdminDashboard as AdminDashboardType } from '../types';
import './AdminDashboard.css';

interface AdminDashboardProps {
  username: string;
  onLogout: () => void;
}

const AdminDashboard: React.FC<AdminDashboardProps> = ({ username, onLogout }) => {
  const [activeTab, setActiveTab] = useState('overview');
  const [dashboard, setDashboard] = useState<AdminDashboardType | null>(null);
  const [pendingBooks, setPendingBooks] = useState<Book[]>([]);
  const [allBooks, setAllBooks] = useState<Book[]>([]);
  const [selectedBook, setSelectedBook] = useState<Book | null>(null);
  const [rejectionReason, setRejectionReason] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadDashboard();
  }, []);

  useEffect(() => {
    if (activeTab === 'pending') {
      loadPendingBooks();
    } else if (activeTab === 'books') {
      loadAllBooks();
    }
  }, [activeTab]);

  const loadDashboard = async () => {
    try {
      const response = await dashboardAPI.getAdminDashboard();
      setDashboard(response.data);
    } catch (err) {
      console.error('Failed to load dashboard:', err);
    } finally {
      setLoading(false);
    }
  };

  const loadPendingBooks = async () => {
    try {
      const response = await adminAPI.getPendingBooks();
      setPendingBooks(response.data);
    } catch (err) {
      console.error('Failed to load pending books:', err);
    }
  };

  const loadAllBooks = async () => {
    try {
      const response = await adminAPI.getAllBooks();
      setAllBooks(response.data);
    } catch (err) {
      console.error('Failed to load books:', err);
    }
  };

  const handleApprove = async (bookId: number) => {
    try {
      await adminAPI.approveBook(bookId, true);
      loadPendingBooks();
      loadDashboard();
      setSelectedBook(null);
    } catch (err) {
      console.error('Failed to approve book:', err);
    }
  };

  const handleReject = async (bookId: number) => {
    if (!rejectionReason.trim()) {
      alert('Please provide a rejection reason');
      return;
    }
    try {
      await adminAPI.approveBook(bookId, false, rejectionReason);
      loadPendingBooks();
      loadDashboard();
      setSelectedBook(null);
      setRejectionReason('');
    } catch (err) {
      console.error('Failed to reject book:', err);
    }
  };

  const handleDelete = async (bookId: number) => {
    if (window.confirm('Are you sure you want to delete this book?')) {
      try {
        await adminAPI.deleteBook(bookId);
        loadAllBooks();
        loadDashboard();
      } catch (err) {
        console.error('Failed to delete book:', err);
      }
    }
  };

  return (
    <div className="admin-dashboard">
      <div className="admin-sidebar">
        <div className="sidebar-header">
          <div className="logo">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
              <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
            </svg>
            <span>Admin Panel</span>
          </div>
          
          <div className="admin-info">
            <div className="admin-avatar">👑</div>
            <div className="admin-details">
              <div className="admin-name">{username}</div>
              <div className="admin-role">Administrator</div>
            </div>
          </div>
        </div>

        <nav className="sidebar-nav">
          <button
            className={activeTab === 'overview' ? 'nav-item active' : 'nav-item'}
            onClick={() => setActiveTab('overview')}
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <rect x="3" y="3" width="7" height="7" />
              <rect x="14" y="3" width="7" height="7" />
              <rect x="14" y="14" width="7" height="7" />
              <rect x="3" y="14" width="7" height="7" />
            </svg>
            <span>Overview</span>
          </button>

          <button
            className={activeTab === 'pending' ? 'nav-item active' : 'nav-item'}
            onClick={() => setActiveTab('pending')}
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="10" />
              <polyline points="12 6 12 12 16 14" />
            </svg>
            <span>Pending Books</span>
            {dashboard && dashboard.pending_books > 0 && (
              <span className="badge">{dashboard.pending_books}</span>
            )}
          </button>

          <button
            className={activeTab === 'books' ? 'nav-item active' : 'nav-item'}
            onClick={() => setActiveTab('books')}
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
              <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
            </svg>
            <span>All Books</span>
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

      <div className="admin-content">
        {activeTab === 'overview' && dashboard && (
          <div className="overview-content">
            <h1>Dashboard Overview</h1>
            
            <div className="stats-grid">
              <div className="stat-card">
                <div className="stat-icon users">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
                    <circle cx="9" cy="7" r="4" />
                    <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
                    <path d="M16 3.13a4 4 0 0 1 0 7.75" />
                  </svg>
                </div>
                <div className="stat-info">
                  <div className="stat-value">{dashboard.total_users}</div>
                  <div className="stat-label">Total Users</div>
                </div>
              </div>

              <div className="stat-card">
                <div className="stat-icon pending">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <circle cx="12" cy="12" r="10" />
                    <polyline points="12 6 12 12 16 14" />
                  </svg>
                </div>
                <div className="stat-info">
                  <div className="stat-value">{dashboard.pending_books}</div>
                  <div className="stat-label">Pending Books</div>
                </div>
              </div>

              <div className="stat-card">
                <div className="stat-icon approved">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
                    <polyline points="22 4 12 14.01 9 11.01" />
                  </svg>
                </div>
                <div className="stat-info">
                  <div className="stat-value">{dashboard.approved_books}</div>
                  <div className="stat-label">Approved Books</div>
                </div>
              </div>

              <div className="stat-card">
                <div className="stat-icon rejected">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <circle cx="12" cy="12" r="10" />
                    <line x1="15" y1="9" x2="9" y2="15" />
                    <line x1="9" y1="9" x2="15" y2="15" />
                  </svg>
                </div>
                <div className="stat-info">
                  <div className="stat-value">{dashboard.rejected_books}</div>
                  <div className="stat-label">Rejected Books</div>
                </div>
              </div>
            </div>

            <div className="users-section">
              <h2>User Leaderboard</h2>
              <div className="users-list">
                {dashboard.users.map((user, index) => (
                  <div key={index} className="user-item">
                    <div className="user-rank">#{index + 1}</div>
                    <div className="user-avatar">{user.username.charAt(0).toUpperCase()}</div>
                    <div className="user-name">{user.username}</div>
                    <div className="user-streak">
                      <svg viewBox="0 0 24 24" fill="currentColor">
                        <path d="M12 2C12 2 7 8 7 12C7 15.31 9.69 18 13 18C16.31 18 19 15.31 19 12C19 8 14 2 14 2H12Z"/>
                      </svg>
                      {user.streak} day streak
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {activeTab === 'pending' && (
          <div className="pending-content">
            <h1>Pending Book Submissions</h1>
            
            {pendingBooks.length === 0 ? (
              <div className="empty-state">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
                  <polyline points="22 4 12 14.01 9 11.01" />
                </svg>
                <h3>All caught up!</h3>
                <p>No pending books to review</p>
              </div>
            ) : (
              <div className="books-list">
                {pendingBooks.map(book => (
                  <div key={book.id} className="book-item">
                    <div className="book-item-info">
                      <h3>{book.title}</h3>
                      <p>by {book.author_name}</p>
                      <div className="book-meta">
                        <span>{book.genre}</span>
                        <span>•</span>
                        <span>{book.category}</span>
                        {book.mood && (
                          <>
                            <span>•</span>
                            <span>{book.mood}</span>
                          </>
                        )}
                      </div>
                      {book.description && (
                        <p className="book-description">{book.description}</p>
                      )}
                    </div>
                    <div className="book-actions">
                      <button
                        onClick={() => setSelectedBook(book)}
                        className="review-btn"
                      >
                        Review
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {activeTab === 'books' && (
          <div className="books-content">
            <h1>All Books</h1>
            
            <div className="books-grid">
              {allBooks.map(book => (
                <div key={book.id} className="book-card-admin">
                  <div className="book-status" style={{
                    background: book.status === 'approved' ? '#4caf50' : book.status === 'pending' ? '#ff9800' : '#f44336'
                  }}>
                    {book.status}
                  </div>
                  <h3>{book.title}</h3>
                  <p>{book.author_name}</p>
                  <div className="book-meta-small">
                    <span>{book.genre}</span>
                    <span>⭐ {book.average_rating.toFixed(1)}</span>
                  </div>
                  <button
                    onClick={() => handleDelete(book.id)}
                    className="delete-btn"
                  >
                    Delete
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {selectedBook && (
        <div className="modal-overlay" onClick={() => setSelectedBook(null)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <button className="modal-close" onClick={() => setSelectedBook(null)}>×</button>
            
            <h2>Review Book Submission</h2>
            
            <div className="book-review-details">
              <div className="detail-row">
                <strong>Title:</strong>
                <span>{selectedBook.title}</span>
              </div>
              <div className="detail-row">
                <strong>Author:</strong>
                <span>{selectedBook.author_name}</span>
              </div>
              <div className="detail-row">
                <strong>Genre:</strong>
                <span>{selectedBook.genre}</span>
              </div>
              <div className="detail-row">
                <strong>Category:</strong>
                <span>{selectedBook.category}</span>
              </div>
              {selectedBook.mood && (
                <div className="detail-row">
                  <strong>Mood:</strong>
                  <span>{selectedBook.mood}</span>
                </div>
              )}
              {selectedBook.description && (
                <div className="detail-row">
                  <strong>Description:</strong>
                  <p>{selectedBook.description}</p>
                </div>
              )}
              <div className="detail-row">
                <strong>Total Pages:</strong>
                <span>{selectedBook.total_pages}</span>
              </div>
            </div>

            <div className="modal-actions">
              <div className="rejection-section">
                <label>Rejection Reason (if rejecting):</label>
                <textarea
                  value={rejectionReason}
                  onChange={(e) => setRejectionReason(e.target.value)}
                  placeholder="Provide a reason if rejecting..."
                  rows={3}
                />
              </div>

              <div className="action-buttons">
                <button
                  onClick={() => handleApprove(selectedBook.id)}
                  className="approve-btn"
                >
                  ✓ Approve
                </button>
                <button
                  onClick={() => handleReject(selectedBook.id)}
                  className="reject-btn"
                >
                  × Reject
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default AdminDashboard;