

const BASE_URL = process.env.REACT_APP_API_URL || 'http://127.0.0.1:8080';

export type Role = 'user' | 'admin';

async function req<T>(
  path: string,
  options: RequestInit = {},
  token?: string
): Promise<T> {
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...(options.headers || {}),
  };
  const res = await fetch(`${BASE_URL}${path}`, { ...options, headers });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `HTTP ${res.status}`);
  }
  try { return await res.json(); } catch { return {} as T; }
}

/* Auth */
export const api = {
  signup: (name: string, email: string, password: string) =>
    req<{ message: string }>('/signup', { method: 'POST', body: JSON.stringify({ name, email, password }) }),

  login: (email: string, password: string) =>
    req<{ access_token: string; token_type: string }>('/login', {
      method: 'POST', body: JSON.stringify({ email, password })
    }),

  adminSignup: (name: string, email: string, password: string) =>
    req<{ message: string }>('/admin/signup', { method: 'POST', body: JSON.stringify({ name, email, password }) }),

  adminLogin: (email: string, password: string) =>
    req<{ access_token: string; token_type: string }>('/admin/login', {
      method: 'POST', body: JSON.stringify({ email, password })
    }),

  /* Admin */
  adminDashboard: (token: string) => req('/admin/dashboard', {}, token),
  adminAddDefaultBook: (token: string, payload: any) =>
    req('/admin/books', { method: 'POST', body: JSON.stringify(payload) }, token),
  adminDeleteBook: (token: string, bookId: number) =>
    req(`/admin/books/${bookId}`, { method: 'DELETE' }, token),
  adminPending: (token: string) => req('/admin/books/pending', {}, token),
  adminApproveReject: (token: string, bookId: number, approve: boolean, reason?: string) =>
    req(`/admin/books/${bookId}/approve`, {
      method: 'POST', body: JSON.stringify({ approve, reason })
    }, token),
  adminAllBooks: (token: string) => req('/admin/books/all', {}, token),
  adminBookReviews: (token: string, bookId: number) => req(`/admin/books/${bookId}/reviews`, {}, token),

  /* User + books */
  createBook: (token: string, payload: any) =>
    req('/books', { method: 'POST', body: JSON.stringify(payload) }, token),
  getBooks: (token?: string) => req('/books', {}, token),
  getBook: (bookId: number, token?: string) => req(`/books/${bookId}`, {}, token),
  getUserBooks: (token: string) => req('/user-books', {}, token),
  addBookToUserList: (token: string, payload: { book_id: number; status: string }) =>
    req('/user-books', { method: 'POST', body: JSON.stringify(payload) }, token),
  updateUserBook: (token: string, userBookId: number, status: string) =>
    req(`/user-books/${userBookId}`, { method: 'PUT', body: JSON.stringify({ status }) }, token),

  /* Reviews */
  createReview: (token: string, bookId: number, payload: { rating: number; recommended: boolean; favorite: boolean; text: string }) =>
    req(`/books/${bookId}/reviews`, { method: 'POST', body: JSON.stringify(payload) }, token),
  getBookReviews: (bookId: number, token?: string) => req(`/books/${bookId}/reviews`, {}, token),

  /* Dashboards */
  userDashboard: (token: string) => req('/dashboard', {}, token),
};
