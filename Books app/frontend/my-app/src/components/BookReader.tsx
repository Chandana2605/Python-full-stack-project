
import React, { useState, useEffect, useCallback } from 'react';
import { bookAPI, userBookAPI, reviewAPI } from '../services/api';
import { Book, BookPage, Review } from '../types';
import './BookReader.css';

interface BookReaderProps {
  book: Book;
  onClose: () => void;
}

const BookReader: React.FC<BookReaderProps> = ({ book, onClose }) => {
  const [pages, setPages] = useState<BookPage[]>([]);
  const [currentPage, setCurrentPage] = useState(0);
  const [reviews, setReviews] = useState<Review[]>([]);
  const [showReviews, setShowReviews] = useState(false);
  const [showAddReview, setShowAddReview] = useState(false);
  const [reviewForm, setReviewForm] = useState({
    rating: 5,
    reviewText: '',
    isRecommended: true
  });
  const [readingStatus, setReadingStatus] = useState<string>('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadBookData();
    // Reset to first page whenever a new book is opened
    setCurrentPage(0);
  }, [book.id]);

  const loadBookData = async () => {
    try {
      const [pagesResponse, reviewsResponse] = await Promise.all([
        bookAPI.getBookPages(book.id),
        reviewAPI.getReviews(book.id)
      ]);
      setPages(pagesResponse.data);
      setReviews(reviewsResponse.data);
    } catch (err) {
      console.error('Failed to load book data:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleAddToList = async (status: string) => {
    try {
      await userBookAPI.addBook(book.id, status);
      setReadingStatus(status);
    } catch (err) {
      console.error('Failed to add to list:', err);
    }
  };

  /**
   * Advance the reader to the next page optimistically.
   * We no longer block page turning on network success.
   */
  const nextPage = useCallback(() => {
    setCurrentPage((prev) => {
      if (prev >= pages.length - 1) return prev; // already at last page
      const next = prev + 1;

      // Fire-and-forget API call to record reading progress
      bookAPI.recordReading(book.id, 1).catch((err) => {
        // We purposely do not roll back UI on failure
        // but we log it for visibility.
        console.error('Failed to record reading:', err);
      });

      return next;
    });
  }, [book.id, pages.length]);

  /**
   * Go to previous page (local only).
   */
  const prevPage = useCallback(() => {
    setCurrentPage((prev) => Math.max(0, prev - 1));
  }, []);

  /**
   * Optional: keyboard navigation (Left/Right arrows)
   */
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'ArrowRight') {
        nextPage();
      } else if (e.key === 'ArrowLeft') {
        prevPage();
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [nextPage, prevPage]);

  const handleSubmitReview = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await reviewAPI.createReview(
        book.id,
        reviewForm.rating,
        reviewForm.reviewText,
        reviewForm.isRecommended
      );
      setShowAddReview(false);
      loadBookData();
    } catch (err) {
      console.error('Failed to submit review:', err);
    }
  };

  if (loading) {
    return (
      <div className="book-reader">
        <div className="loading-container">
          <div className="spinner"></div>
          <p>Loading book...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="book-reader">
      <div className="reader-header">
        <button onClick={onClose} className="back-btn">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M19 12H5M12 19l-7-7 7-7"/>
          </svg>
          Back
        </button>

        <div className="reader-actions">
          <button onClick={() => setShowReviews(!showReviews)} className="action-btn">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M12 17.27L18.18 21l-1.64-7.03L22 9.24l-7.19-.61L12 2 9.19 8.63 2 9.24l5.46 4.73L5.82 21z"/>
            </svg>
            Reviews ({reviews.length})
          </button>

          {!readingStatus && (
            <div className="add-to-list-dropdown">
              <button className="action-btn primary">Add to List</button>
              <div className="dropdown-menu">
                <button onClick={() => handleAddToList('wish_to_read')}>Want to Read</button>
                <button onClick={() => handleAddToList('currently_reading')}>Currently Reading</button>
                <button onClick={() => handleAddToList('completed')}>Completed</button>
              </div>
            </div>
          )}
        </div>
      </div>

      <div className="reader-content">
        {!showReviews ? (
          <div className="book-reading-area">
            <div className="book-info-header">
              <h1>{book.title}</h1>
              <p className="author">by {book.author_name}</p>
              <div className="book-meta-info">
                <span className="genre-badge">{book.genre}</span>
                {book.mood && <span className="mood-badge">{book.mood}</span>}
                <span className="rating-badge">⭐ {book.average_rating.toFixed(1)}</span>
              </div>
              {book.description && (
                <p className="description">{book.description}</p>
              )}
            </div>

            {pages.length > 0 ? (
              <>
                <div className="page-content">
                  <div className="page-number">Page {currentPage + 1} of {pages.length}</div>
                  <div className="page-text">{pages[currentPage].content}</div>
                </div>

                <div className="page-navigation">
                  <button
                    onClick={prevPage}
                    disabled={currentPage <= 0}
                    className="nav-btn"
                  >
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M15 18l-6-6 6-6"/>
                    </svg>
                    Previous
                  </button>

                  <div className="page-indicator">
                    {currentPage + 1} / {pages.length}
                  </div>

                  <button
                    onClick={nextPage}
                    disabled={currentPage >= pages.length - 1}
                    className="nav-btn"
                  >
                    Next
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M9 18l6-6-6-6"/>
                    </svg>
                  </button>
                </div>
              </>
            ) : (
              <div className="no-pages">
                <p>No pages available for this book yet.</p>
              </div>
            )}
          </div>
        ) : (
          <div className="reviews-section">
            <div className="reviews-header">
              <h2>Reviews</h2>
              <button onClick={() => setShowAddReview(!showAddReview)} className="add-review-btn">
                Write a Review
              </button>
            </div>

            {showAddReview && (
              <form onSubmit={handleSubmitReview} className="review-form">
                <div className="rating-input">
                  <label>Rating</label>
                  <div className="star-rating">
                    {[1, 2, 3, 4, 5].map(star => (
                      <button
                        key={star}
                        type="button"
                        onClick={() => setReviewForm({ ...reviewForm, rating: star })}
                        className={star <= reviewForm.rating ? 'star active' : 'star'}
                      >
                        ★
                      </button>
                    ))}
                  </div>
                </div>

                <div className="form-field">
                  <label>Your Review</label>
                  <textarea
                    value={reviewForm.reviewText}
                    onChange={(e) => setReviewForm({ ...reviewForm, reviewText: e.target.value })}
                    placeholder="Share your thoughts about this book..."
                    rows={5}
                  />
                </div>

                <div className="form-checkbox">
                  <input
                    type="checkbox"
                    checked={reviewForm.isRecommended}
                    onChange={(e) => setReviewForm({ ...reviewForm, isRecommended: e.target.checked })}
                    id="recommend"
                  />
                  <label htmlFor="recommend">I recommend this book</label>
                </div>

                <button type="submit" className="submit-review-btn">Submit Review</button>
              </form>
            )}

            <div className="reviews-list">
              {reviews.length === 0 ? (
                <div className="no-reviews">
                  <p>No reviews yet. Be the first to review!</p>
                </div>
              ) : (
                reviews.map(review => (
                  <div key={review.id} className="review-card">
                    <div className="review-header">
                      <div className="reviewer-avatar">
                        {review.username?.[0].toUpperCase() || 'U'}
                      </div>
                      <div>
                        <div className="reviewer-name">{review.username || 'Anonymous'}</div>
                        <div className="review-rating">
                          {'★'.repeat(Math.round(review.rating))}
                          {'☆'.repeat(5 - Math.round(review.rating))}
                        </div>
                      </div>
                      {review.is_recommended && (
                        <span className="recommended-badge">Recommended</span>
                      )}
                    </div>
                    {review.review_text && (
                      <p className="review-text">{review.review_text}</p>
                    )}
                  </div>
                ))
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default BookReader;
