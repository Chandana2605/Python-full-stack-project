
import React, { useState, useEffect } from 'react';
import Auth from './components/Auth';
import UserDashboard from './components/UserDashboard';
import AdminDashboard from './components/AdminDashboard';
import { authAPI } from './services/api';
import './App.css';

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [role, setRole] = useState<string>('');
  const [username, setUsername] = useState<string>('');
  const [loading, setLoading] = useState(true);

  // Validate token on first load
  useEffect(() => {
    const token = localStorage.getItem('token');

    if (!token) {
      setLoading(false);
      return;
    }

    authAPI.me()
      .then((res) => {
        const savedRole = res.data.role;
        const savedUsername = res.data.username;

        // In case role/username were missing previously
        localStorage.setItem('role', savedRole);
        localStorage.setItem('username', savedUsername);

        setIsAuthenticated(true);
        setRole(savedRole);
        setUsername(savedUsername);
      })
      .catch(() => {
        // Token invalid/expired
        localStorage.removeItem('token');
        localStorage.removeItem('role');
        localStorage.removeItem('username');
        setIsAuthenticated(false);
        setRole('');
        setUsername('');
      })
      .finally(() => {
        setLoading(false);
      });
  }, []);

  // Optional: sync logout across tabs
  useEffect(() => {
    const handler = (e: StorageEvent) => {
      if (e.key === 'token' && !e.newValue) {
        setIsAuthenticated(false);
        setRole('');
        setUsername('');
      }
    };
    window.addEventListener('storage', handler);
    return () => window.removeEventListener('storage', handler);
  }, []);

  const handleLogin = (token: string, userRole: string, userName: string) => {
    localStorage.setItem('token', token);
    localStorage.setItem('role', userRole);
    localStorage.setItem('username', userName);

    setIsAuthenticated(true);
    setRole(userRole);
    setUsername(userName);
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('role');
    localStorage.removeItem('username');
    setIsAuthenticated(false);
    setRole('');
    setUsername('');
  };

  if (loading) {
    return (
      <div className="app-loading">
        <div className="spinner"></div>
        <p>Loading...</p>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Auth onLogin={handleLogin} />;
  }

  return (
    <div className="app">
      {role === 'admin' ? (
        <AdminDashboard username={username} onLogout={handleLogout} />
      ) : (
        <UserDashboard username={username} onLogout={handleLogout} />
      )}
    </div>
  );
}

export default App;
