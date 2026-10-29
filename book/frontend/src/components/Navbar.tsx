
import React from "react";
import { useAuth } from "../authContext";
import "./../App.css";

type Page =
  | "books" | "book" | "login" | "signup"
  | "userDashboard" | "adminDashboard" | "createBook";

export const Navbar: React.FC<{
  page: Page;
  setPage: (p: Page) => void;
}> = ({ page, setPage }) => {
  const { token, role, logout } = useAuth();

  return (
    <div className="nav">
      <div className="nav-inner">
        <div className="brand">📚 Book Finder</div>

        <div className="nav-items">
          <button className={`tab ${page === "books" ? "active" : ""}`} onClick={() => setPage("books")}>
            🔍 Explore
          </button>
          {!!token && role === "user" && (
            <button className={`tab ${page === "userDashboard" ? "active" : ""}`} onClick={() => setPage("userDashboard")}>
              🧑‍💻 My Dashboard
            </button>
          )}
          {!!token && role === "admin" && (
            <>
              <button className={`tab ${page === "adminDashboard" ? "active" : ""}`} onClick={() => setPage("adminDashboard")}>
                🛠️ Admin
              </button>
            </>
          )}
          {!token && (
            <>
              <button className={`tab ${page === "login" ? "active" : ""}`} onClick={() => setPage("login")}>
                🔐 Login
              </button>
              <button className={`tab ${page === "signup" ? "active" : ""}`} onClick={() => setPage("signup")}>
                ✍️ Signup
              </button>
            </>
          )}
          {!!token && (
            <button className="tab" onClick={logout}>
              🚪 Logout
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
