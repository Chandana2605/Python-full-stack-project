
export type Status = 'currently_reading' | 'completed' | 'wish_to_read';

export interface Book {
  id: number;
  title: string;
  author?: string;
  genre?: string;
  mood?: string;
  category?: string;
  rating?: number;       // average rating
  description?: string;
  status?: 'approved' | 'pending' | 'rejected';
  postedBy?: string;
  isDefault?: boolean;
}

export interface Review {
  id: number;
  book_id: number;
  rating: number;
  recommended: boolean;
  favorite: boolean;
  text: string;
  user_name: string;
}

export interface UserBook {
  id: number;
  book_id: number;
  status: Status;
}

export interface UserDashboard {
  streak: number;
  favorites: Book[];
  completed: Book[];
  currently_reading: Book[];
  wish_to_read: Book[];
  posted_books: Book[];
  favourite_genre?: string;
}

export interface AdminUser {
  id: number;
  name: string;
  email: string;
  streak: number;
}

export interface AdminDashboard {
  users_count: number;
  users: AdminUser[];
}
