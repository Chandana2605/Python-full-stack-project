import React, { useState } from 'react';
import { bookAPI } from '../services/api';
import './AddBook.css';

interface AddBookProps {
  onSuccess: () => void;
}

const AddBook: React.FC<AddBookProps> = ({ onSuccess }) => {
  const [formData, setFormData] = useState({
    title: '',
    author: '',
    genre: '',
    category: '',
    mood: '',
    description: '',
  });
  const [pages, setPages] = useState(['']);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const bookData = {
        ...formData,
        pages: pages.filter(p => p.trim() !== ''),
      };

      await bookAPI.createBook(bookData);
      setSuccess(true);
      setTimeout(() => {
        onSuccess();
        resetForm();
      }, 2000);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to create book');
    } finally {
      setLoading(false);
    }
  };

  const resetForm = () => {
    setFormData({
      title: '',
      author: '',
      genre: '',
      category: '',
      mood: '',
      description: '',
    });
    setPages(['']);
    setSuccess(false);
  };

  const addPage = () => {
    setPages([...pages, '']);
  };

  const removePage = (index: number) => {
    setPages(pages.filter((_, i) => i !== index));
  };

  const updatePage = (index: number, content: string) => {
    const newPages = [...pages];
    newPages[index] = content;
    setPages(newPages);
  };

  const genres = ['Fantasy', 'Science Fiction', 'Mystery', 'Romance', 'Thriller', 'Self-Help', 'Biography', 'Historical Fiction', 'Horror', 'Adventure'];
  const moods = ['Magical', 'Exciting', 'Inspiring', 'Dark', 'Uplifting', 'Thought-provoking', 'Relaxing', 'Intense'];

  if (success) {
    return (
      <div className="success-message">
        <div className="success-icon">✓</div>
        <h2>Book Submitted!</h2>
        <p>Your book has been submitted for review by an admin.</p>
      </div>
    );
  }

  return (
    <div className="add-book">
      <div className="add-book-header">
        <h1>Share Your Book 📖</h1>
        <p>Submit your book for review</p>
      </div>

      <form onSubmit={handleSubmit} className="add-book-form">
        <div className="form-section">
          <h3>Book Details</h3>
          
          <div className="form-grid">
            <div className="form-field">
              <label>Title *</label>
              <input
                type="text"
                value={formData.title}
                onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                required
                placeholder="Enter book title"
              />
            </div>

            <div className="form-field">
              <label>Author *</label>
              <input
                type="text"
                value={formData.author}
                onChange={(e) => setFormData({ ...formData, author: e.target.value })}
                required
                placeholder="Enter author name"
              />
            </div>

            <div className="form-field">
              <label>Genre *</label>
              <select
                value={formData.genre}
                onChange={(e) => setFormData({ ...formData, genre: e.target.value })}
                required
              >
                <option value="">Select genre</option>
                {genres.map(genre => (
                  <option key={genre} value={genre}>{genre}</option>
                ))}
              </select>
            </div>

            <div className="form-field">
              <label>Category *</label>
              <select
                value={formData.category}
                onChange={(e) => setFormData({ ...formData, category: e.target.value })}
                required
              >
                <option value="">Select category</option>
                <option value="Fiction">Fiction</option>
                <option value="Non-Fiction">Non-Fiction</option>
              </select>
            </div>

            <div className="form-field">
              <label>Mood</label>
              <select
                value={formData.mood}
                onChange={(e) => setFormData({ ...formData, mood: e.target.value })}
              >
                <option value="">Select mood</option>
                {moods.map(mood => (
                  <option key={mood} value={mood}>{mood}</option>
                ))}
              </select>
            </div>
          </div>

          <div className="form-field">
            <label>Description</label>
            <textarea
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              placeholder="Describe your book..."
              rows={4}
            />
          </div>
        </div>

        <div className="form-section">
          <div className="section-header">
            <h3>Book Pages</h3>
            <button type="button" onClick={addPage} className="add-page-btn">
              + Add Page
            </button>
          </div>

          {pages.map((page, index) => (
            <div key={index} className="page-field">
              <div className="page-header">
                <label>Page {index + 1}</label>
                {pages.length > 1 && (
                  <button
                    type="button"
                    onClick={() => removePage(index)}
                    className="remove-page-btn"
                  >
                    Remove
                  </button>
                )}
              </div>
              <textarea
                value={page}
                onChange={(e) => updatePage(index, e.target.value)}
                placeholder="Enter page content..."
                rows={6}
              />
            </div>
          ))}
        </div>

        {error && <div className="error-alert">{error}</div>}

        <button type="submit" className="submit-btn" disabled={loading}>
          {loading ? 'Submitting...' : 'Submit Book'}
        </button>
      </form>
    </div>
  );
};

export default AddBook;