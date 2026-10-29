import { useState } from "react";

import { InlineAlert } from "../components/Ui";

export function LoginPage({ onLogin }) {
  const [form, setForm] = useState({ email: "", password: "" });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setLoading(true);
    try {
      await onLogin(form);
    } catch (submitError) {
      setError(submitError.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="login-page">
      <div className="login-panel">
        <div className="login-panel__hero">
          <div className="brand__mark brand__mark--large">CH</div>
          <div className="page-header__eyebrow">Enterprise Workspace</div>
          <h1>Campus Hire Tracker</h1>
          <p>
            Unified operations console for batch planning, archives, rule governance, and candidate
            movement across onboarding phases.
          </p>
        </div>
        <form className="login-form" onSubmit={handleSubmit}>
          <div className="form-grid form-grid--single">
            <label className="field">
              <span>Email</span>
              <input
                type="email"
                value={form.email}
                onChange={(event) => setForm((current) => ({ ...current, email: event.target.value }))}
                placeholder="manager@company.com"
                required
              />
            </label>
            <label className="field">
              <span>Password</span>
              <input
                type="password"
                value={form.password}
                onChange={(event) => setForm((current) => ({ ...current, password: event.target.value }))}
                placeholder="Enter your password"
                required
              />
            </label>
          </div>
          <InlineAlert tone="danger" message={error} />
          <button className="button button--primary button--full" disabled={loading} type="submit">
            {loading ? "Signing in..." : "Sign in to workspace"}
          </button>
        </form>
      </div>
    </div>
  );
}
