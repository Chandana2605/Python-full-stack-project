
import React, { useState } from 'react';
import { authAPI } from '../services/api';
import './Auth.css';

interface AuthProps {
  onLogin: (token: string, role: string, username: string) => void;
}

const Auth: React.FC<AuthProps> = ({ onLogin }) => {
  const [isLogin, setIsLogin] = useState(true);
  const [isAdmin, setIsAdmin] = useState(false);
  const [formData, setFormData] = useState({
    email: '',
    username: '',
    password: '',
  });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      let response;
      
      if (isLogin) {
        response = isAdmin 
          ? await authAPI.adminLogin(formData.email, formData.password)
          : await authAPI.login(formData.email, formData.password);
      } else {
        response = isAdmin
          ? await authAPI.adminSignup(formData.email, formData.username, formData.password)
          : await authAPI.signup(formData.email, formData.username, formData.password);
      }

      const { access_token, role, username } = response.data;

      // Delegate all persistence to App via onLogin
      onLogin(access_token, role, username);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Authentication failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-container">
      <div className="auth-background"></div>
      
      <div className="auth-card">
        <div className="auth-header">
          <div className="book-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
              <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
            </svg>
          </div>
          <h1>BookFinder</h1>
          <p>Your Personal Reading Journey</p>
        </div>

        <div className="auth-toggle">
          <button
            className={!isAdmin ? 'active' : ''}
            onClick={() => setIsAdmin(false)}
          >
            User
          </button>
          <button
            className={isAdmin ? 'active' : ''}
            onClick={() => setIsAdmin(true)}
          >
            Admin
          </button>
        </div>

        <form onSubmit={handleSubmit} className="auth-form">
          <div className="form-group">
            <input
              type="email"
              placeholder="Email address"
              value={formData.email}
              onChange={(e) => setFormData({ ...formData, email: e.target.value })}
              required
            />
          </div>

          {!isLogin && (
            <div className="form-group">
              <input
                type="text"
                placeholder="Username"
                value={formData.username}
                onChange={(e) => setFormData({ ...formData, username: e.target.value })}
                required
              />
            </div>
          )}

          <div className="form-group">
            <input
              type="password"
              placeholder="Password"
              value={formData.password}
              onChange={(e) => setFormData({ ...formData, password: e.target.value })}
              required
            />
          </div>

          {error && <div className="error-message">{error}</div>}

          <button type="submit" className="submit-button" disabled={loading}>
            {loading ? 'Please wait...' : (isLogin ? 'Sign In' : 'Create Account')}
          </button>

          <div className="auth-switch">
            {isLogin ? "Don't have an account? " : "Already have an account? "}
            <button type="button" onClick={() => {
              setIsLogin(!isLogin);
              setError('');
            }}>
              {isLogin ? 'Sign Up' : 'Sign In'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default Auth;
