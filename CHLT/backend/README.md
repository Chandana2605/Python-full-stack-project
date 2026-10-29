# L&D Management Backend

FastAPI backend for the internal Learning and Development management platform.

## Local setup

1. Create a virtual environment and install dependencies from `requirements.txt`.
2. Copy `.env.example` to `.env`.
3. Update MongoDB and Outlook SMTP settings.
4. Start MongoDB locally.
5. Run the API with `uvicorn app.main:app --reload` from the `backend` directory.

## Invitation email flow

- Admin creates a Batch Owner or Program Manager.
- Backend stores the temporary password as a hash and sets `force_password_change=true`.
- Backend sends an invitation email to the user email ID with:
  - login email
  - temporary password
  - platform login link
  - instruction to change password on first login
- If Outlook SMTP is disabled or delivery fails, the API still creates the user and returns the delivery status.
- Backend stores delivery metadata on the user record: `invitation_email_sent`, `invitation_sent_at`, `invitation_last_attempt_at`, `invitation_last_error`.
- Admin can reset the temporary password and resend the invitation using `POST /api/v1/admin/users/{user_id}/resend-invitation`.
- Admin can verify the SMTP trigger using `POST /api/v1/admin/email/test`.

## Required Outlook SMTP configuration

Set these in `.env`:

- `SMTP_ENABLED=true`
- `SMTP_HOST=smtp.office365.com`
- `SMTP_PORT=587`
- `SMTP_USERNAME`
- `SMTP_PASSWORD`
- `SMTP_SENDER_EMAIL`
- `SMTP_SENDER_NAME`
- `FRONTEND_LOGIN_URL`

Example request bodies:

`POST /api/v1/admin/users/{user_id}/resend-invitation`

```json
{
  "temporary_password": "NewTempPass123!"
}
```

`POST /api/v1/admin/email/test`

```json
{
  "recipient_email": "test.user@company.com"
}
```

Notes:

- Use the Outlook or Microsoft 365 mailbox credentials in `SMTP_USERNAME` and `SMTP_PASSWORD`.
- The sender email should typically match the authenticated mailbox or be an allowed send-as address in Microsoft 365.
- If SMTP AUTH is disabled for the mailbox or tenant, Outlook SMTP delivery will fail until it is enabled.
