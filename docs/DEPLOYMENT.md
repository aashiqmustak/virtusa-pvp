# Deployment Guide: Render (Backend + Database) & Vercel (Frontend)

This guide walks you through deploying the **MSME Underwriting Desk** to **Render** for the backend API and PostgreSQL database, and **Vercel** for the Vue 3 frontend portal.

---

## Architecture Overview

```
                      ┌───────────────────────────────────────┐
                      │             User Browser              │
                      └───────────┬────────────────┬──────────┘
                                  │                │
            HTTPS (Static Assets) │                │ HTTPS / WSS (API & Voice)
                                  ▼                ▼
                     ┌──────────────────┐   ┌────────────────────────┐
                     │      Vercel      │   │         Render         │
                     │  (Client / SPA)  │   │  (Docker Web Service)  │
                     └──────────────────┘   └───────────┬────────────┘
                                                        │
                                                        │ PostgreSQL Protocol
                                                        ▼
                                            ┌────────────────────────┐
                                            │    Render Postgres     │
                                            │      (Database)        │
                                            └────────────────────────┘
```

- **Frontend (Vercel)**: Vue 3 + TypeScript + Vite Single Page Application.
- **Backend (Render Web Service)**: Litestar + Uvicorn + Tesseract OCR running in a lightweight Docker container.
- **Database (Render Postgres)**: Managed PostgreSQL database for applicant, journey, evidence, and audit logs.

---

## Part 1: Deploy Backend & Database to Render

### Method A: One-Click via Render Blueprint (Recommended)

The repository includes a ready-to-use `render.yaml` specification.

1. Push your repository to **GitHub** or **GitLab**.
2. Log in to your [Render Dashboard](https://dashboard.render.com/).
3. Click **New +** and select **Blueprint**.
4. Connect your GitHub/GitLab repository.
5. Render will detect `render.yaml` and prompt you to create:
   - **`msme-db`**: A PostgreSQL database (Free tier).
   - **`msme-backend`**: A Docker web service connected to the database.
6. Click **Apply**.
7. Once deployed, note down:
   - Your backend URL: `https://msme-backend-xxxx.onrender.com`
   - Your staff tokens: Go to **msme-backend** → **Environment** → find `ANALYST_TOKEN` and `REVIEWER_TOKEN` (or replace them with values you choose).

---

### Method B: Manual Setup on Render Dashboard

If you prefer to configure services manually:

#### Step 1: Create PostgreSQL Database
1. In Render, click **New +** → **PostgreSQL**.
2. Set:
   - **Name**: `msme-db`
   - **Database**: `msme`
   - **User**: `msme`
   - **Plan**: `Free`
3. Click **Create Database**.
4. Once ready, copy the **Internal Database URL** (e.g. `postgres://msme:...@dpg-.../msme`).

#### Step 2: Create Docker Web Service
1. Click **New +** → **Web Service**.
2. Connect your GitHub repository.
3. Configure the settings:
   - **Name**: `msme-backend`
   - **Region**: Same region as your database (e.g., Oregon)
   - **Runtime**: **Docker**
   - **Dockerfile Path**: `server/Dockerfile`
   - **Docker Context**: `.` (root directory of the repo)
   - **Instance Type**: `Free`
4. Add the following **Environment Variables**:

| Variable | Value | Description |
|---|---|---|
| `DATABASE_URL` | *(Paste your Postgres Internal Connection URL)* | Automatically formatted to `postgresql+psycopg://` |
| `PORT` | `8000` | Port listened to by Uvicorn |
| `CORS_ALLOWED_ORIGINS` | `*` *(or your Vercel URL once known)* | Allows browser requests from Vercel |
| `VOICE_ALLOWED_ORIGINS` | `*` *(or your Vercel URL)* | Allows WebSocket connections |
| `ANALYST_TOKEN` | `analyst-secret-demo-token` | Token used to sign in as Credit Officer |
| `REVIEWER_TOKEN` | `reviewer-secret-demo-token` | Token used to sign in as Branch Manager |
| `VOICE_MODE` | `mock` | `mock` for text interview, or `sarvam` for live speech |
| `SARVAM_API_KEY` | *(Optional)* | Only needed if `VOICE_MODE=sarvam` |
| `LLM_MODE` | `mock` | Deterministic demo narrative |
| `POLICY_FILE` | `/workspace/policy.demo.json` | Loan policy configuration |
| `PRIVATE_STORAGE` | `/data/uploads` | Path for synthetic document uploads |

5. Click **Create Web Service**.
6. When the build finishes and shows **"Live"**, verify by visiting:
   ```
   https://<your-render-app>.onrender.com/api/health
   ```
   You should see `{"status":"ok"}`.

---

## Part 2: Deploy Frontend to Vercel

1. Log in to [Vercel](https://vercel.com).
2. Click **Add New...** → **Project**.
3. Import your Git repository.
4. In the **Configure Project** screen:
   - **Project Name**: `msme-capital` (or any name you choose)
   - **Framework Preset**: `Vite`
   - **Root Directory**: Click **Edit** and select **`client`** (important!)
   - **Build Command**: `npm run build` (default)
   - **Output Directory**: `dist` (default)
5. Under **Environment Variables**, add:
   - **Key**: `VITE_API_BASE_URL`
   - **Value**: `https://<your-render-app>.onrender.com` (do not add a trailing slash)
6. Click **Deploy**.
7. Vercel will install dependencies, build the Vue 3 app, and assign you a URL like `https://msme-capital-xxxx.vercel.app`.

---

## Part 3: Test & Verify

1. Open your Vercel URL in your browser:
   `https://<your-app>.vercel.app`
2. **Borrower Portal**:
   - Select a synthetic business profile (e.g., `SYN-0001`).
   - Click **Continue to verification** → Enter the 6-digit demo OTP shown on screen.
   - Complete synthetic KYC verification.
   - Accept the 5 consents, choose loan terms, and submit.
3. **Credit Staff Portal**:
   - Click **Credit workspace ↗** in the top navigation.
   - Enter your `ANALYST_TOKEN` from Render's environment variables.
   - Find the submitted application, verify details, and run analysis.
4. **Branch Manager**:
   - Sign in with your `REVIEWER_TOKEN` to approve rate exceptions and complete final sanction.
   - Check the **Sanction register** to view the ledger.
5. **Voice Interview**:
   - In **Verification & terms**, start the interview.
   - In `VOICE_MODE=mock`, type your answers and verify completion.

---

## Common Questions & Troubleshooting

### 1. Database Connection Strings (`postgres://` vs `postgresql+psycopg://`)
Render PostgreSQL supplies connection strings starting with `postgres://` or `postgresql://`. Standard SQLAlchemy fails if `psycopg2` is not installed.
The backend has been configured to automatically normalize all Postgres connection strings to `postgresql+psycopg://` so it works out of the box with `psycopg 3`.

### 2. CORS Errors
If your browser console displays a CORS policy error when accessing the API from Vercel:
- Ensure `CORS_ALLOWED_ORIGINS` on Render is set to `*` or explicitly includes your exact Vercel URL (e.g. `https://my-app.vercel.app`).

### 3. Voice Interview WebSocket Disconnections
- When running across two different domains (Vercel frontend and Render backend), WebSockets connect directly to `wss://<your-render-app>.onrender.com/api/voice/socket`.
- Ensure `VOICE_ALLOWED_ORIGINS` on Render is set to `*` or includes your Vercel URL.
- Render Web Services natively support persistent WebSocket connections.

### 4. Render Free Tier Spin-Down
Render's free tier spins down web services after 15 minutes of inactivity. When you make the first request from Vercel after an idle period, it may take 30–50 seconds for the backend container to wake up. This is normal for free tier instances.

