import { NavLink, useLocation } from "react-router-dom";

import { formatEnum } from "../utils/format";
import { StatusBadge } from "./Ui";

function Navigation({ items }) {
  return (
    <nav className="nav">
      {items.map((item) => (
        <NavLink
          key={item.to}
          to={item.to}
          className={({ isActive }) => `nav__item${isActive ? " nav__item--active" : ""}`}
        >
          <span className="nav__label">{item.label}</span>
          <span className="nav__caption">{item.caption}</span>
        </NavLink>
      ))}
    </nav>
  );
}

export function AppShell({ user, title, subtitle, navItems, onLogout, accent = "manager", children }) {
  const location = useLocation();
  const activeItem = navItems.find((item) => location.pathname.startsWith(item.to)) ?? navItems[0];

  return (
    <div className="shell" data-accent={accent}>
      <aside className="sidebar">
        <div className="brand brand--stacked">
          <div className="brand__mark">CH</div>
          <div>
            <div className="brand__title">Campus Hire Tracker</div>
            <div className="brand__subtitle">Talent operations workspace</div>
          </div>
        </div>

        <div className="sidebar__panel">
          <div className="sidebar__eyebrow">Role Surface</div>
          <div className="sidebar__headline">{formatEnum(user.role)}</div>
          <p className="sidebar__copy">Purpose-built controls, tabs, and workflow visibility for the responsibilities owned by this role.</p>
          <StatusBadge tone="info">{user.mustChangePassword ? "Password Reset Required" : "Secure Session Active"}</StatusBadge>
        </div>

        <div className="sidebar__section">
          <div className="sidebar__eyebrow">Navigation</div>
          <Navigation items={navItems} />
        </div>

        <div className="sidebar__footer">
          <div className="identity">
            <div className="identity__role">{formatEnum(user.role)}</div>
            <div className="identity__email">{user.email}</div>
          </div>
          <button className="button button--ghost button--full" onClick={onLogout} type="button">
            Sign out
          </button>
        </div>
      </aside>

      <main className="content">
        <div className="content__inner">
          <div className="content-topbar">
            <div className="content-topbar__section">
              <span className="content-topbar__label">Current Workspace</span>
              <strong>{activeItem?.label ?? "Workspace"}</strong>
            </div>
            <div className="content-topbar__section">
              <span className="content-topbar__label">Signed in as</span>
              <strong>{user.email}</strong>
            </div>
          </div>
          <header className="page-header">
            <div>
              <div className="page-header__eyebrow">Enterprise Operations Suite</div>
              <h1>{title}</h1>
              <p>{subtitle}</p>
            </div>
          </header>
          {children}
        </div>
      </main>
    </div>
  );
}
