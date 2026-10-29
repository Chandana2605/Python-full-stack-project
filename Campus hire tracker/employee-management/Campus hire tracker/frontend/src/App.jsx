import { Navigate, Route, Routes, useLocation } from "react-router-dom";

import { AppShell } from "./components/AppShell";
import { BatchOwnerPage } from "./pages/BatchOwnerPage";
import { ChangePasswordPage } from "./pages/ChangePasswordPage";
import { LndDashboardPage } from "./pages/LndDashboardPage";
import { LoginPage } from "./pages/LoginPage";
import { ProgramManagerPage } from "./pages/ProgramManagerPage";
import { useAuth } from "./state/AuthContext";

const roleConfigs = {
  LND_MANAGER: {
    accent: "manager",
    title: "L&D Manager Workspace",
    subtitle:
      "Manage yearly hiring data, assessment uploads, training batches, user access, approvals, and year-wise visibility from one role-specific workspace.",
    defaultPath: "/app/lnd/master-data",
    navItems: [
      { to: "/app/lnd/master-data", label: "Master Database", caption: "Yearly hires and candidate records" },
      { to: "/app/lnd/exams", label: "Exams", caption: "Baseline and knowledge check uploads" },
      { to: "/app/lnd/batches", label: "Batches", caption: "Year grid, phases, batches, owners" },
      { to: "/app/lnd/configuration", label: "Configuration", caption: "Rule change requests" },
      { to: "/app/lnd/requests", label: "Dropout / Resignation", caption: "Review and revoke requests" },
      { to: "/app/lnd/archives", label: "Year Archives", caption: "Past years and candidate timelines" },
      { to: "/app/lnd/analytics", label: "Analytics", caption: "Lifecycle and year comparison view" },
      { to: "/app/lnd/users", label: "User Management", caption: "Create batch owners and program managers" }
    ]
  },
  BATCH_OWNER: {
    accent: "owner",
    title: "Batch Owner Workspace",
    subtitle:
      "Set up assigned batches, manage candidate progress, update marks and employment details, handle assessments, and raise dropout or resignation requests.",
    defaultPath: "/app/batch-owner/setup",
    navItems: [
      { to: "/app/batch-owner/setup", label: "Batch Setup", caption: "Batch details and phase-based assignment" },
      { to: "/app/batch-owner/my-batch", label: "My Batch", caption: "Roster, timeline, export, updates" },
      { to: "/app/batch-owner/exams", label: "Exams", caption: "Manual and bulk score updates" },
      { to: "/app/batch-owner/requests", label: "Dropout / Resignation", caption: "Submit and track requests" }
    ]
  },
  PROGRAM_MANAGER: {
    accent: "program",
    title: "Program Manager Workspace",
    subtitle:
      "Review assigned batches in read-only mode and handle rule configuration requests raised by the L&D Manager.",
    defaultPath: "/app/program-manager/batches",
    navItems: [
      { to: "/app/program-manager/batches", label: "Assigned Batches", caption: "Program batches and candidate view" },
      { to: "/app/program-manager/rule-requests", label: "Rule Requests", caption: "Configuration request monitoring" }
    ]
  }
};

function getSectionFromPath(pathname) {
  const parts = pathname.split("/").filter(Boolean);
  return parts[2] ?? "";
}

function getHomePath(role) {
  return roleConfigs[role]?.defaultPath ?? "/login";
}

function ProtectedLayout() {
  const location = useLocation();
  const { isAuthenticated, user, accessToken, logout, changePassword } = useAuth();

  if (!isAuthenticated || !user) {
    return <Navigate replace to="/login" state={{ from: location }} />;
  }

  if (user.mustChangePassword) {
    return <ChangePasswordPage email={user.email} onSubmit={changePassword} />;
  }

  const config = roleConfigs[user.role];

  if (location.pathname === "/app/lnd" && user.role === "LND_MANAGER") {
    return <Navigate replace to={config.defaultPath} />;
  }

  if (location.pathname === "/app/batch-owner" && user.role === "BATCH_OWNER") {
    return <Navigate replace to={config.defaultPath} />;
  }

  if (location.pathname === "/app/program-manager" && user.role === "PROGRAM_MANAGER") {
    return <Navigate replace to={config.defaultPath} />;
  }

  const currentSection = getSectionFromPath(location.pathname);
  const pageByRole = {
    LND_MANAGER: <LndDashboardPage token={accessToken} section={currentSection || "master-data"} />,
    BATCH_OWNER: <BatchOwnerPage token={accessToken} section={currentSection || "setup"} />,
    PROGRAM_MANAGER: <ProgramManagerPage token={accessToken} section={currentSection || "batches"} />
  };

  return (
    <AppShell
      user={user}
      title={config.title}
      subtitle={config.subtitle}
      navItems={config.navItems}
      accent={config.accent}
      onLogout={logout}
    >
      {pageByRole[user.role]}
    </AppShell>
  );
}

export default function App() {
  const { isAuthenticated, login, user, changePassword } = useAuth();

  return (
    <Routes>
      <Route
        path="/login"
        element={
          isAuthenticated ? (
            user?.mustChangePassword ? (
              <ChangePasswordPage email={user.email} onSubmit={changePassword} />
            ) : (
              <Navigate replace to={getHomePath(user?.role)} />
            )
          ) : (
            <LoginPage onLogin={login} />
          )
        }
      />
      <Route path="/app/*" element={<ProtectedLayout />} />
      <Route path="*" element={<Navigate replace to="/login" />} />
    </Routes>
  );
}
