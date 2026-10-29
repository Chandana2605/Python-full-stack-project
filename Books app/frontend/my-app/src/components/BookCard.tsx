import React from 'react';
import { Book } from '../types';
import './BookCard.css';

interface BookCardProps {
  book: Book;
  onSelect: () => void;
  isFavorite?: boolean;
  showStatus?: boolean;
}

const BookCard: React.FC<BookCardProps> = ({ book, onSelect, isFavorite, showStatus }) => {
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'approved': return '#4caf50';
      case 'pending': return '#ff9800';
      case 'rejected': return '#f44336';
      default: return '#999';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'approved': return '✓';
      case 'pending': return '⏳';
      case 'rejected': return '✗';
      default: return '';
    }
  };

  return (
    <div className="book-card" onClick={onSelect}>
      <div className="book-cover">
        <div className="cover-gradient" style={{
          background: `linear-gradient(135deg, ${getRandomGradient(book.id)})`
        }}>
          <div className="cover-content">
            <div className="book-icon-large">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
                <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
              </svg>
            </div>
          </div>
        </div>
        
        {isFavorite && (
          <div className="favorite-badge">
            <svg viewBox="0 0 24 24" fill="currentColor">
              <path d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z"/>
            </svg>
          </div>
        )}
        
        {showStatus && (
          <div className="status-badge" style={{ background: getStatusColor(book.status) }}>
            {getStatusIcon(book.status)} {book.status}
          </div>
        )}
        
        <div className="book-rating">
          <svg viewBox="0 0 24 24" fill="currentColor">
            <path d="M12 17.27L18.18 21l-1.64-7.03L22 9.24l-7.19-.61L12 2 9.19 8.63 2 9.24l5.46 4.73L5.82 21z"/>
          </svg>
          <span>{book.average_rating.toFixed(1)}</span>
        </div>
      </div>
      
      <div className="book-info">
        <h3 className="book-title">{book.title}</h3>
        <p className="book-author">{book.author_name}</p>
        
        <div className="book-meta">
          <span className="book-genre">{book.genre}</span>
          {book.mood && <span className="book-mood">{book.mood}</span>}
        </div>
        
        <div className="book-stats">
          <span>{book.total_pages} pages</span>
          <span>•</span>
          <span>{book.total_reviews} reviews</span>
        </div>
      </div>
    </div>
  );
};

function getRandomGradient(seed: number): string {
  const gradients = [
    '#667eea 0%, #764ba2 100%',
    '#f093fb 0%, #f5576c 100%',
    '#4facfe 0%, #00f2fe 100%',
    '#43e97b 0%, #38f9d7 100%',
    '#fa709a 0%, #fee140 100%',
    '#30cfd0 0%, #330867 100%',
    '#a8edea 0%, #fed6e3 100%',
    '#ff9a9e 0%, #fecfef 100%',
  ];
  return gradients[seed % gradients.length];
}

export default BookCard;