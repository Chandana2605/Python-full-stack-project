import { useState } from "react";

import { InlineAlert } from "../components/Ui";

export function ChangePasswordPage({ email, onSubmit }) {
  const [form, setForm] = useState({ current_password: "", new_password: "", confirm_password: "" });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");

    if (form.new_password !== form.confirm_password) {
      setError("New password and confirmation do not match.");
      return;
    }

    setLoading(true);

    try {
      await onSubmit({
        current_password: form.current_password,
        new_password: form.new_password
      });
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
          <div className="page-header__eyebrow">Security Setup</div>
          <h1>Set your new password</h1>
          <p>
            Your account was created with a temporary password. Complete this one-time setup to access
            your role-based workspace.
          </p>
        </div>
        <form className="login-form" onSubmit={handleSubmit}>
          <div className="form-grid form-grid--single">
            <label className="field">
              <span>Email</span>
              <input disabled value={email} />
            </label>
            <label className="field">
              <span>Current temporary password</span>
              <input
                required
                type="password"
                value={form.current_password}
                onChange={(event) => setForm((current) => ({ ...current, current_password: event.target.value }))}
              />
            </label>
            <label className="field">
              <span>New password</span>
              <input
                required
                minLength="8"
                type="password"
                value={form.new_password}
                onChange={(event) => setForm((current) => ({ ...current, new_password: event.target.value }))}
              />
            </label>
            <label className="field">
              <span>Confirm new password</span>
              <input
                required
                minLength="8"
                type="password"
                value={form.confirm_password}
                onChange={(event) => setForm((current) => ({ ...current, confirm_password: event.target.value }))}
              />
            </label>
          </div>
          <InlineAlert tone="danger" message={error} />
          <button className="button button--primary button--full" disabled={loading} type="submit">
            {loading ? "Updating password..." : "Continue to workspace"}
          </button>
        </form>
      </div>
    </div>
  );
}
