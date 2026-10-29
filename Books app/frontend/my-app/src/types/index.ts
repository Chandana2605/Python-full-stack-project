export interface User {
  id: number;
  email: string;
  username: string;
  role: string;
  current_streak: number;
}

export interface Book {
  id: number;
  title: string;
  author_name: string;
  genre: string;
  category: string;
  mood?: string;
  description?: string;
  average_rating: number;
  total_reviews: number;
  total_pages: number;
  status: string;
  is_default: boolean;
  rejection_reason?: string;
  created_at: string;
}

export interface UserBook {
  id: number;
  book_id: number;
  reading_status: string;
  is_favorite: boolean;
  current_page: number;
  book?: Book;
}

export interface Review {
  id: number;
  user_id: number;
  book_id: number;
  rating: number;
  review_text?: string;
  is_recommended: boolean;
  created_at: string;
  username?: string;
}

export interface BookPage {
  id: number;
  book_id: number;
  page_number: number;
  content: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  role: string;
  username: string;
}

export interface Dashboard {
  username: string;
  streak: number;
  favorites: Book[];
  currently_reading: Book[];
  completed: Book[];
  wish_to_read: Book[];
  posted_books: Book[];
  favorite_genre?: string;
}

export interface AdminDashboard {
  total_users: number;
  users: { username: string; streak: number }[];
  pending_books: number;
  approved_books: number;
  rejected_books: number;
}