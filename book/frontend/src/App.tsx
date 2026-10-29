
import React, { useState } from "react";
import { AuthProvider } from "./authContext";
import { Navbar } from "./components/Navbar";
import { BookList } from "./pages/BookList";
import { BookDetails } from "./pages/BookDetails";
import { Login } from "./pages/Login";
import { Signup } from "./pages/Signup";
import { UserDashboard } from "./pages/UserDashboard";
import { AdminDashboard } from "./pages/AdminDashboard";
import { Book } from "./types";
import "./App.css";

type Page =
  | "books" | "book" | "login" | "signup"
  | "userDashboard" | "adminDashboard";

const AppShell: React.FC = () => {
  const [page, setPage] = useState<Page>("books");
  const [selectedBookId, setSelectedBookId] = useState<number | null>(null);

  const openDetails = (b: Book) => { setSelectedBookId(b.id); setPage("book"); };

  return (
    <div className="app">
      <Navbar page={page} setPage={setPage} />

      {page === "books" && <BookList onDetails={openDetails} />}
      {page === "book" && <BookDetails bookId={selectedBookId} />}
      {page === "login" && <Login />}
      {page === "signup" && <Signup />}
      {page === "userDashboard" && <UserDashboard onDetails={openDetails} />}
      {page === "adminDashboard" && <AdminDashboard onDetails={openDetails} />}
    </div>
  );
};

const App: React.FC = () => (
  <AuthProvider>
    <AppShell />
  </AuthProvider>
);

export default App;
