# SocialMedia AI Secure Scheduler

SocialMedia AI is a social media content planner built with a FastAPI backend and React/Vite frontend. It supports post planning, queue management, analytics, AI scoring, preview studio, saved preferences, and like/dislike feedback for future dataset training.

## Production-clean version

This ZIP is cleaned for live deployment:

- No demo posts are seeded.
- No demo accounts are seeded.
- No demo access tokens are included.
- Login fields are blank in the UI.
- Admin credentials are loaded only from environment variables.
- `.env` is not included. Use `.env.example` locally and Railway Variables online.

## Backend setup

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

For local use, copy `.env.example` to `.env` and set your own credentials:

```env
ADMIN_EMAIL=your-admin-email@example.com
ADMIN_PASSWORD=your-strong-password
SECRET_KEY=your-long-random-secret
ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
FRONTEND_URL=http://localhost:5173
```

## Frontend setup

```bash
cd frontend
npm install
npm run dev
```

For local use, create `frontend/.env`:

```env
VITE_API_URL=http://localhost:8000
```

## Railway backend start command

Set the backend root directory to `backend` and use:

```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Add these Railway Variables in the backend service:

```env
ADMIN_EMAIL=your-real-admin-email
ADMIN_PASSWORD=your-real-strong-password
SECRET_KEY=your-long-random-secret-key
ALLOWED_ORIGINS=https://your-frontend-domain
FRONTEND_URL=https://your-frontend-domain
META_APP_ID=
META_APP_SECRET=
META_GRAPH_VERSION=v19.0
META_REDIRECT_URI=https://your-backend-domain/oauth/meta/callback
```

## Railway frontend setup

Set the frontend root directory to `frontend`.

Build command:

```bash
npm install && npm run build
```

Start command:

```bash
npm start
```

Add this Railway Variable in the frontend service:

```env
VITE_API_URL=https://your-backend-domain
```

## Notes

SQLite is used for a simple demo database. For long-term production use, upgrade to PostgreSQL or Supabase because Railway redeploys may not keep local SQLite data unless persistent storage is configured.


## Optional sample content for presentation

The production-clean build does not auto-load demo data. After logging in locally or on Railway, open the Content Calendar and click **Load sample content**. This adds safe sample posts and demo channel names for Instagram, Facebook, LinkedIn, Twitter, YouTube, TikTok, and Pinterest. No real access tokens are added.

You can also call this backend endpoint after login:

```bash
POST /demo/seed
```

Use this only for testing or project demonstration. For a real client account, create real channels from the Channels page and delete the sample posts.
