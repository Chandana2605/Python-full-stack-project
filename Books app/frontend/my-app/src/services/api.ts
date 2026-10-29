
import axios from 'axios';
import { AuthResponse, Book, UserBook, Review, BookPage, Dashboard, AdminDashboard } from '../types';

const API_URL = 'http://localhost:8080';

const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add auth token to requests
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error?.response?.status === 401) {
      localStorage.removeItem('token');
      localStorage.removeItem('role');
      localStorage.removeItem('username');

      if (window.location.pathname !== '/') {
        window.location.href = '/';
      }
    }
    return Promise.reject(error);
  }
);

export const authAPI = {
  login: (email: string, password: string) =>
    api.post<AuthResponse>('/login', { email, password }),
  
  signup: (email: string, username: string, password: string) =>
    api.post<AuthResponse>('/signup', { email, username, password }),
  
  adminLogin: (email: string, password: string) =>
    api.post<AuthResponse>('/admin/login', { email, password }),
  
  adminSignup: (email: string, username: string, password: string) =>
    api.post<AuthResponse>('/admin/signup', { email, username, password }),


  me: () => api.get<{ role: string; username: string }>('/me'),
};

// Book APIs
export const bookAPI = {
  getBooks: (filters?: { genre?: string; mood?: string; category?: string; min_rating?: number }) =>
    api.get<Book[]>('/books', { params: filters }),
  
  getBook: (id: number) =>
    api.get<Book>(`/books/${id}`),
  
  createBook: (bookData: any) =>
    api.post<Book>('/books', bookData),
  
  getBookPages: (bookId: number) =>
    api.get<BookPage[]>(`/books/${bookId}/pages`),
  
  recordReading: (bookId: number, pagesRead: number) =>
    api.post(`/books/${bookId}/read`, { pages_read: pagesRead }),
};

// User Book APIs
export const userBookAPI = {
  getUserBooks: () =>
    api.get<UserBook[]>('/user-books'),
  
  addBook: (bookId: number, status: string) =>
    api.post<UserBook>('/user-books', { book_id: bookId, reading_status: status }),
  
  updateBook: (userBookId: number, data: { reading_status?: string; is_favorite?: boolean }) =>
    api.put<UserBook>(`/user-books/${userBookId}`, data),
};

// Review APIs
export const reviewAPI = {
  getReviews: (bookId: number) =>
    api.get<Review[]>(`/books/${bookId}/reviews`),
  
  createReview: (bookId: number, rating: number, reviewText?: string, isRecommended?: boolean) =>
    api.post<Review>(`/books/${bookId}/reviews`, {
      rating,
      review_text: reviewText,
      is_recommended: isRecommended ?? true,
    }),
};

// Dashboard APIs
export const dashboardAPI = {
  getUserDashboard: () =>
    api.get<Dashboard>('/dashboard'),
  
  getAdminDashboard: () =>
    api.get<AdminDashboard>('/admin/dashboard'),
};

// Admin APIs
export const adminAPI = {
  getPendingBooks: () =>
    api.get<Book[]>('/admin/books/pending'),
  
  getAllBooks: () =>
    api.get<Book[]>('/admin/books/all'),
  
  approveBook: (bookId: number, approved: boolean, rejectionReason?: string) =>
    api.post(`/admin/books/${bookId}/approve`, { approved, rejection_reason: rejectionReason }),
  
  deleteBook: (bookId: number) =>
    api.delete(`/admin/books/${bookId}`),
  
  addDefaultBook: (bookData: any) =>
    api.post<Book>('/admin/books', bookData),
  
  getBookReviews: (bookId: number) =>
    api.get<Review[]>(`/admin/books/${bookId}/reviews`),
};

export default api;
