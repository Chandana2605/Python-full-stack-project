# Internal L&D Platform Backend

FastAPI backend for a local Learning & Development platform using PostgreSQL.

## Run Locally

1. Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

2. Start PostgreSQL locally and confirm `.env` values:

```env
SECRET_KEY=super-secret-key-change-me
DATABASE_URL=postgresql://postgres:postgres@localhost:5000/training_platform
ACCESS_TOKEN_EXPIRE_MINUTES=480
```

3. Seed the first L&D Manager:

```powershell
python -m app.scripts.seed
```

4. Run the API:

```powershell
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000/docs`.

## Frontend

A React frontend is scaffolded in `frontend/`.

Run locally:

```powershell
cd frontend
npm install
npm run dev
```

The UI expects the backend at `http://127.0.0.1:8000/api/v1` by default.

To override it:

```powershell
$env:VITE_API_BASE_URL="http://127.0.0.1:8000/api/v1"
```

## Auth Model

Login is role-agnostic. `POST /api/v1/auth/login` accepts only `email` and `password`; the API reads the role from PostgreSQL and returns access and refresh tokens with `must_change_password`.

Users created by the L&D Manager receive a temporary password and are blocked from normal protected workflows until they call `POST /api/v1/auth/change-password`.

## Main API Groups

`POST /api/v1/auth/login`: role-agnostic login. Accepts JSON `email`/`password` and also Swagger form login.

`POST /api/v1/auth/refresh`: accepts a refresh token and returns a fresh access token pair.

`POST /api/v1/auth/change-password`: change first-login temporary password or current password.

`/api/v1/lnd-manager/users`: create and list Batch Owner and Program Manager users.

`/api/v1/lnd-manager/training-batches`: create and view training batches.

`/api/v1/lnd-manager/candidate-master-records`: create candidate master records.

`/api/v1/lnd-manager/dropout-resignation-requests`: view and review Batch Owner dropout/resignation requests.

`/api/v1/batch-owner/assigned-batches`: Batch Owner assigned batch workflows.

`/api/v1/batch-owner/assigned-batches/{batch_id}/eligible-candidates`: list only unassigned candidates eligible for that batch phase.

`/api/v1/batch-owner/assigned-batches/{batch_id}/candidates/{candidate_id}/employment-details`: update UID and employee email for post-onboarding batches.

`/api/v1/batch-owner/dropout-resignation-requests`: view owner-submitted dropout or resignation requests.

`/api/v1/program-manager/assigned-program-batches`: Program Manager read-only assigned batch access.

## Main Roles

`LND_MANAGER`: creates Batch Owners and Program Managers, creates batches and candidates, reviews pending dropout/resignation requests, and has read-only batch access.

`BATCH_OWNER`: fully implemented workflow for assigned batches only, including phase-restricted candidate assignment, candidate timelines, search/filter/export, manual marks, post-onboarding UID and employee email updates, pre/post onboarding exams, sample template download, Excel upload, and dropout/resignation request submission.

`PROGRAM_MANAGER`: limited read-only access to batches assigned to that program manager.

## Excel Upload Columns

`GET /api/v1/batch-owner/assigned-batches/exam-results/template` returns a sample CSV template.

`POST /api/v1/batch-owner/assigned-batches/{batch_id}/exam-results/excel-upload` accepts `.xlsx` with columns:

```text
candidate_id, phase, exam_type, custom_exam_name, attempt, score, max_score, pass_percentage
```

`phase` must be `PRE_ONBOARDING` or `POST_ONBOARDING`.

`exam_type` can be `FOUNDATION_EXAM`, `MODULE_EXAM`, `ADVANCED_EXAM`, `FINAL_EXAM`, or `CUSTOM_EXAM`.

If `exam_type` is `CUSTOM_EXAM`, `custom_exam_name` is required.

`pass_percentage` is optional and defaults to `60`.
