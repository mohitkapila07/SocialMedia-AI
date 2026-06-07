import os
from dotenv import load_dotenv
load_dotenv()
import csv
import json
import sqlite3
import secrets
import shutil
import math
from urllib.parse import urlencode
from urllib.request import urlopen
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Any

from fastapi import Depends, FastAPI, Header, HTTPException, Request, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel
from fastapi.staticfiles import StaticFiles
try:
    from PIL import Image, ImageStat
except Exception:
    Image = None
    ImageStat = None

APP_NAME = "SocialMedia AI Scheduler API"
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "").strip()
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")
SECRET_KEY = os.getenv("SECRET_KEY", "").strip()
ALLOWED_ORIGINS = [x.strip() for x in os.getenv("ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")]

app = FastAPI(title=APP_NAME, version="3.1.0", docs_url="/swagger", redoc_url="/redoc")
UPLOAD_DIR = Path(__file__).resolve().parent.parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")

class LoginRequest(BaseModel):
    email: str
    password: str

class PostCreate(BaseModel):
    title: str
    platform: str
    post_type: str = "image"
    content: str = ""
    scheduled_at: datetime
    status: str = "Scheduled"
    location: str = "Online"
    occasion: str = "General"
    media_url: Optional[str] = None
    media_type: Optional[str] = None
    media_score: Optional[int] = None
    ai_score: Optional[int] = None
    ai_details: Optional[dict[str, Any]] = None
    is_saved: bool = False
    preference_notes: Optional[str] = None
    like_count: int = 0
    dislike_count: int = 0

class Post(PostCreate):
    id: int

class StatusUpdate(BaseModel):
    status: str

class AccountCreate(BaseModel):
    platform: str
    name: str
    access_token: Optional[str] = None
    status: str = "Connected"

class Account(BaseModel):
    id: int
    platform: str
    name: str
    status: str = "Connected"
    token_saved: bool = False

class Settings(BaseModel):
    brand_name: str = "SocialMedia AI"
    default_platform: str = "Instagram"
    default_time: str = "10:00"
    theme: str = "dark"
    notifications: bool = True

class PreferenceUpdate(BaseModel):
    is_saved: bool = True
    preference_notes: Optional[str] = None

class FeedbackCreate(BaseModel):
    feedback: str
    reason: Optional[str] = None

class FeedbackRecord(BaseModel):
    id: int
    post_id: int
    feedback: str
    reason: Optional[str] = None
    created_at: datetime
    post_title: Optional[str] = None
    platform: Optional[str] = None
    post_type: Optional[str] = None

# Production-clean store. Data is loaded from SQLite; no demo posts, demo accounts, or demo tokens are seeded.
posts: list[Post] = []
accounts: list[Account] = []
# Private tokens are intentionally stored separately and never returned by any API.
_private_tokens: dict[int, str] = {}
sessions: dict[str, datetime] = {}
next_post_id = 1
next_account_id = 1
settings = Settings()


DEMO_PLATFORM_NAMES = ["Instagram", "Facebook", "LinkedIn", "Twitter", "YouTube", "TikTok", "Pinterest"]


def _demo_schedule(day_offset: int, hour: int, minute: int = 0) -> datetime:
    base = datetime.utcnow().replace(hour=hour, minute=minute, second=0, microsecond=0)
    return base + timedelta(days=day_offset)


def _sample_demo_posts() -> list[PostCreate]:
    """Optional presentation/demo content. It is never seeded automatically."""
    return [
        PostCreate(
            title="Instagram Reel: Product Styling Tips",
            platform="Instagram",
            post_type="reel",
            content="A 20-second reel showing quick styling tips, smooth transitions and a clear save-for-later CTA.",
            scheduled_at=_demo_schedule(1, 18, 30),
            status="Scheduled",
            location="Instagram Reels",
            occasion="Product Awareness",
            media_url="https://images.unsplash.com/photo-1496747611176-843222e1e57c?auto=format&fit=crop&w=1200&q=80",
            media_type="image",
            media_score=88,
            ai_score=91,
            ai_details={"reason": "Short-form visual content usually performs well in evening slots."},
            is_saved=True,
            preference_notes="Use this format for future reel demos.",
            like_count=7,
            dislike_count=1,
        ),
        PostCreate(
            title="Facebook Post: Weekend Offer Announcement",
            platform="Facebook",
            post_type="image",
            content="Weekend offer announcement with benefit-focused caption and shop-now CTA for local customers.",
            scheduled_at=_demo_schedule(2, 11, 0),
            status="Ready",
            location="Facebook Page",
            occasion="Weekend Campaign",
            media_url="https://images.unsplash.com/photo-1515886657613-9f3515b0c78f?auto=format&fit=crop&w=1200&q=80",
            media_type="image",
            media_score=81,
            ai_score=84,
            ai_details={"reason": "Midday community posts are suitable for Facebook page engagement."},
            like_count=5,
        ),
        PostCreate(
            title="LinkedIn Update: Monthly Growth Report",
            platform="LinkedIn",
            post_type="text",
            content="A professional update summarizing monthly growth, campaign learning and next-quarter content goals.",
            scheduled_at=_demo_schedule(3, 10, 0),
            status="Drafting",
            location="LinkedIn Company Page",
            occasion="Business Update",
            media_score=72,
            ai_score=86,
            ai_details={"reason": "Professional updates generally perform better during office hours."},
            like_count=3,
        ),
        PostCreate(
            title="Twitter Thread: 5 Content Ideas for Brands",
            platform="Twitter",
            post_type="text",
            content="Thread idea: five practical content ideas, one example per post, ending with a question to drive replies.",
            scheduled_at=_demo_schedule(4, 16, 0),
            status="Idea",
            location="X / Twitter Profile",
            occasion="Educational Thread",
            ai_score=79,
            ai_details={"reason": "Threads with direct tips can generate saves and replies."},
            like_count=4,
        ),
        PostCreate(
            title="YouTube Short: New Feature Walkthrough",
            platform="YouTube",
            post_type="video",
            content="Short video showing how the Preview Studio saves preferences and collects like/dislike feedback.",
            scheduled_at=_demo_schedule(5, 19, 0),
            status="Scheduled",
            location="YouTube Shorts",
            occasion="Feature Launch",
            media_url="https://images.unsplash.com/photo-1611162617474-5b21e879e113?auto=format&fit=crop&w=1200&q=80",
            media_type="image",
            media_score=85,
            ai_score=89,
            is_saved=True,
            preference_notes="Good demo for explaining the feedback training feature.",
            like_count=6,
        ),
        PostCreate(
            title="TikTok Demo: Before and After Editing",
            platform="TikTok",
            post_type="reel",
            content="Fast before/after edit using trending audio, subtitles and a final CTA to follow for more tips.",
            scheduled_at=_demo_schedule(6, 20, 30),
            status="Ready",
            location="TikTok Business",
            occasion="Short Video Demo",
            media_url="https://images.unsplash.com/photo-1611162616475-46b635cb6868?auto=format&fit=crop&w=1200&q=80",
            media_type="image",
            media_score=90,
            ai_score=92,
            like_count=8,
            dislike_count=1,
        ),
        PostCreate(
            title="Pinterest Pin: Campaign Moodboard",
            platform="Pinterest",
            post_type="carousel",
            content="A visual moodboard pin showing colors, product combinations and seasonal inspiration for future campaigns.",
            scheduled_at=_demo_schedule(7, 12, 30),
            status="Posted",
            location="Pinterest Board",
            occasion="Moodboard Inspiration",
            media_url="https://images.unsplash.com/photo-1529139574466-a303027c1d8b?auto=format&fit=crop&w=1200&q=80",
            media_type="image",
            media_score=87,
            ai_score=83,
            is_saved=True,
            preference_notes="Good visual style for product moodboards.",
            like_count=9,
        ),
    ]


def _sample_demo_accounts() -> list[Account]:
    return [
        Account(id=0, platform="Instagram", name="Instagram Business Demo", status="Demo Connected", token_saved=False),
        Account(id=0, platform="Facebook", name="Facebook Page Demo", status="Demo Connected", token_saved=False),
        Account(id=0, platform="LinkedIn", name="LinkedIn Company Demo", status="Demo Connected", token_saved=False),
        Account(id=0, platform="Twitter", name="X / Twitter Demo", status="Demo Connected", token_saved=False),
        Account(id=0, platform="YouTube", name="YouTube Channel Demo", status="Demo Connected", token_saved=False),
        Account(id=0, platform="TikTok", name="TikTok Business Demo", status="Demo Connected", token_saved=False),
        Account(id=0, platform="Pinterest", name="Pinterest Board Demo", status="Demo Connected", token_saved=False),
    ]


def _seed_demo_content(replace: bool = False) -> dict[str, int]:
    """Load sample presentation content only when the admin requests it."""
    global posts, accounts, next_post_id, next_account_id
    if replace:
        posts = []
        accounts = []
        _private_tokens.clear()
        next_post_id = 1
        next_account_id = 1
        _replace_all_posts(posts)
        with _db() as conn:
            conn.execute("DELETE FROM accounts")

    added_posts = 0
    existing_post_keys = {(p.platform.lower(), p.title.lower()) for p in posts}
    for sample in _sample_demo_posts():
        key = (sample.platform.lower(), sample.title.lower())
        if key in existing_post_keys:
            continue
        post = Post(id=next_post_id, **sample.model_dump())
        next_post_id += 1
        posts.append(post)
        _save_post(post)
        existing_post_keys.add(key)
        added_posts += 1

    added_accounts = 0
    existing_account_keys = {(a.platform.lower(), a.name.lower()) for a in accounts}
    for sample in _sample_demo_accounts():
        key = (sample.platform.lower(), sample.name.lower())
        if key in existing_account_keys:
            continue
        account = sample.model_copy(update={"id": next_account_id})
        next_account_id += 1
        accounts.append(account)
        _save_account(account, None)
        existing_account_keys.add(key)
        added_accounts += 1

    return {"posts_added": added_posts, "accounts_added": added_accounts, "total_posts": len(posts), "total_accounts": len(accounts)}


DB_PATH = Path(os.getenv("DATABASE_PATH", str(Path(__file__).resolve().parent.parent / "socialmedia.sqlite3")))
FEEDBACK_DATASET_PATH = Path(__file__).resolve().parent.parent / "data" / "feedback_training.csv"


def _db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _post_json(post: Post) -> str:
    return json.dumps(post.model_dump(mode="json"), ensure_ascii=False)


def _account_json(account: Account) -> str:
    return json.dumps(account.model_dump(mode="json"), ensure_ascii=False)


def _init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _db() as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS posts (id INTEGER PRIMARY KEY, data TEXT NOT NULL)")
        conn.execute("CREATE TABLE IF NOT EXISTS accounts (id INTEGER PRIMARY KEY, data TEXT NOT NULL, access_token TEXT)")
        conn.execute("CREATE TABLE IF NOT EXISTS settings (id INTEGER PRIMARY KEY CHECK (id=1), data TEXT NOT NULL)")
        conn.execute("CREATE TABLE IF NOT EXISTS sessions (token TEXT PRIMARY KEY, expires_at TEXT NOT NULL)")
        conn.execute("""CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id INTEGER NOT NULL,
            feedback TEXT NOT NULL,
            reason TEXT,
            created_at TEXT NOT NULL,
            post_snapshot TEXT NOT NULL
        )""")
        if conn.execute("SELECT COUNT(*) FROM posts").fetchone()[0] == 0:
            for p in posts:
                conn.execute("INSERT INTO posts (id, data) VALUES (?, ?)", (p.id, _post_json(p)))
        if conn.execute("SELECT COUNT(*) FROM accounts").fetchone()[0] == 0:
            for a in accounts:
                conn.execute("INSERT INTO accounts (id, data, access_token) VALUES (?, ?, ?)", (a.id, _account_json(a), _private_tokens.get(a.id)))
        if conn.execute("SELECT COUNT(*) FROM settings").fetchone()[0] == 0:
            conn.execute("INSERT INTO settings (id, data) VALUES (1, ?)", (json.dumps(settings.model_dump(mode="json")),))


def _load_store():
    global posts, accounts, _private_tokens, sessions, next_post_id, next_account_id, settings
    with _db() as conn:
        post_rows = conn.execute("SELECT data FROM posts ORDER BY id").fetchall()
        posts = [Post.model_validate(json.loads(r["data"])) for r in post_rows]
        account_rows = conn.execute("SELECT id, data, access_token FROM accounts ORDER BY id").fetchall()
        accounts = [Account.model_validate(json.loads(r["data"])) for r in account_rows]
        _private_tokens = {int(r["id"]): r["access_token"] for r in account_rows if r["access_token"]}
        session_rows = conn.execute("SELECT token, expires_at FROM sessions WHERE expires_at > ?", (datetime.utcnow().isoformat(),)).fetchall()
        sessions = {r["token"]: datetime.fromisoformat(r["expires_at"]) for r in session_rows}
        row = conn.execute("SELECT data FROM settings WHERE id=1").fetchone()
        settings = Settings.model_validate(json.loads(row["data"])) if row else Settings()
    next_post_id = (max([p.id for p in posts]) + 1) if posts else 1
    next_account_id = (max([a.id for a in accounts]) + 1) if accounts else 1


def _save_post(post: Post):
    with _db() as conn:
        conn.execute("INSERT OR REPLACE INTO posts (id, data) VALUES (?, ?)", (post.id, _post_json(post)))


def _delete_post_db(post_id: int):
    with _db() as conn:
        conn.execute("DELETE FROM posts WHERE id=?", (post_id,))


def _replace_all_posts(new_posts: list[Post]):
    with _db() as conn:
        conn.execute("DELETE FROM posts")
        for p in new_posts:
            conn.execute("INSERT INTO posts (id, data) VALUES (?, ?)", (p.id, _post_json(p)))


def _save_account(account: Account, access_token: Optional[str] = None):
    with _db() as conn:
        old = conn.execute("SELECT access_token FROM accounts WHERE id=?", (account.id,)).fetchone()
        token = access_token if access_token else (old["access_token"] if old else None)
        conn.execute("INSERT OR REPLACE INTO accounts (id, data, access_token) VALUES (?, ?, ?)", (account.id, _account_json(account), token))


def _delete_account_db(account_id: int):
    with _db() as conn:
        conn.execute("DELETE FROM accounts WHERE id=?", (account_id,))


def _save_settings(payload: Settings):
    with _db() as conn:
        conn.execute("INSERT OR REPLACE INTO settings (id, data) VALUES (1, ?)", (json.dumps(payload.model_dump(mode="json"), ensure_ascii=False),))


def _save_session(token: str, expiry: datetime):
    with _db() as conn:
        conn.execute("INSERT OR REPLACE INTO sessions (token, expires_at) VALUES (?, ?)", (token, expiry.isoformat()))


def _feedback_bonus(platform: str, post_type: str) -> int:
    """Small preference signal learned from direct like/dislike feedback."""
    with _db() as conn:
        rows = conn.execute("SELECT feedback, post_snapshot FROM feedback").fetchall()
    score = 0
    for r in rows:
        try:
            snap = json.loads(r["post_snapshot"])
        except Exception:
            continue
        if str(snap.get("platform", "")).lower() == platform.lower() and str(snap.get("post_type", "")).lower() == post_type.lower():
            score += 4 if r["feedback"] == "like" else -4
    return max(-12, min(12, score))


def _append_feedback_dataset(post: Post, feedback: str, reason: str | None):
    FEEDBACK_DATASET_PATH.parent.mkdir(parents=True, exist_ok=True)
    exists = FEEDBACK_DATASET_PATH.exists()
    with FEEDBACK_DATASET_PATH.open("a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["created_at", "post_id", "title", "platform", "post_type", "scheduled_at", "occasion", "ai_score", "media_score", "feedback", "reason"])
        if not exists:
            writer.writeheader()
        writer.writerow({
            "created_at": datetime.utcnow().isoformat(),
            "post_id": post.id,
            "title": post.title,
            "platform": post.platform,
            "post_type": post.post_type,
            "scheduled_at": post.scheduled_at.isoformat(),
            "occasion": post.occasion,
            "ai_score": post.ai_score or "",
            "media_score": post.media_score or "",
            "feedback": feedback,
            "reason": reason or "",
        })


def _record_feedback(post: Post, feedback: str, reason: str | None):
    created_at = datetime.utcnow()
    with _db() as conn:
        cur = conn.execute(
            "INSERT INTO feedback (post_id, feedback, reason, created_at, post_snapshot) VALUES (?, ?, ?, ?, ?)",
            (post.id, feedback, reason, created_at.isoformat(), _post_json(post)),
        )
        feedback_id = cur.lastrowid
    _append_feedback_dataset(post, feedback, reason)
    return feedback_id, created_at


_init_db()
_load_store()


def require_configured_auth():
    if not ADMIN_EMAIL or not ADMIN_PASSWORD or not SECRET_KEY:
        raise HTTPException(status_code=500, detail="Server auth is not configured. Set ADMIN_EMAIL, ADMIN_PASSWORD, and SECRET_KEY in Railway variables.")

def create_session() -> str:
    token = secrets.token_urlsafe(32)
    expiry = datetime.utcnow() + timedelta(hours=12)
    sessions[token] = expiry
    _save_session(token, expiry)
    return token


def require_auth(authorization: Optional[str] = Header(default=None)):
    require_configured_auth()
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Login required")
    token = authorization.replace("Bearer ", "", 1)
    expiry = sessions.get(token)
    if not expiry or expiry < datetime.utcnow():
        raise HTTPException(status_code=401, detail="Session expired")
    return {"email": ADMIN_EMAIL}


def check_cookie(request: Request):
    token = request.cookies.get("sm_admin_token")
    return bool(token and sessions.get(token) and sessions[token] > datetime.utcnow())

@app.get("/")
def root():
    return {"message": "SocialMedia AI API running", "admin_ui": "/admin", "api_ui": "/docs", "swagger": "/swagger"}

@app.post("/auth/login")
def login(payload: LoginRequest):
    require_configured_auth()
    if payload.email.lower().strip() == ADMIN_EMAIL.lower() and payload.password == ADMIN_PASSWORD:
        return {"access_token": create_session(), "token_type": "bearer", "user": {"email": ADMIN_EMAIL, "role": "Admin"}}
    raise HTTPException(status_code=401, detail="Invalid email or password")

@app.get("/auth/me")
def me(user=Depends(require_auth)):
    return {"email": user["email"], "role": "Admin"}

@app.get("/posts", response_model=list[Post])
def get_posts(month: Optional[int] = None, year: Optional[int] = None, platform: Optional[str] = None, status: Optional[str] = None, user=Depends(require_auth)):
    data = posts
    if month and year:
        data = [p for p in data if p.scheduled_at.month == month and p.scheduled_at.year == year]
    if platform and platform != "All":
        data = [p for p in data if p.platform == platform]
    if status and status != "All":
        data = [p for p in data if p.status == status]
    return data

@app.post("/posts", response_model=Post)
def create_post(payload: PostCreate, user=Depends(require_auth)):
    global next_post_id
    post = Post(id=next_post_id, **payload.model_dump())
    next_post_id += 1
    posts.append(post)
    _save_post(post)
    return post

@app.put("/posts/{post_id}", response_model=Post)
def update_post(post_id: int, payload: PostCreate, user=Depends(require_auth)):
    for i, post in enumerate(posts):
        if post.id == post_id:
            updated = Post(id=post_id, **payload.model_dump())
            posts[i] = updated
            _save_post(updated)
            return updated
    raise HTTPException(status_code=404, detail="Post not found")


@app.patch("/posts/{post_id}/status", response_model=Post)
def update_post_status(post_id: int, payload: StatusUpdate, user=Depends(require_auth)):
    valid = {"Idea", "Drafting", "Ready", "Scheduled", "Posted"}
    if payload.status not in valid:
        raise HTTPException(status_code=400, detail="Invalid workflow status")
    for i, post in enumerate(posts):
        if post.id == post_id:
            updated = post.model_copy(update={"status": payload.status})
            posts[i] = updated
            _save_post(updated)
            return updated
    raise HTTPException(status_code=404, detail="Post not found")

@app.delete("/posts/{post_id}")
def delete_post(post_id: int, user=Depends(require_auth)):
    for i, post in enumerate(posts):
        if post.id == post_id:
            removed = posts.pop(i)
            _delete_post_db(post_id)
            return {"deleted": True, "post": removed}
    raise HTTPException(status_code=404, detail="Post not found")

@app.get("/accounts", response_model=list[Account])
def get_accounts(user=Depends(require_auth)):
    return accounts

@app.post("/accounts", response_model=Account)
def create_account(payload: AccountCreate, user=Depends(require_auth)):
    global next_account_id
    account = Account(id=next_account_id, platform=payload.platform, name=payload.name, status=payload.status, token_saved=bool(payload.access_token))
    if payload.access_token:
        _private_tokens[next_account_id] = payload.access_token
    next_account_id += 1
    accounts.append(account)
    _save_account(account, payload.access_token)
    return account

@app.delete("/accounts/{account_id}")
def delete_account(account_id: int, user=Depends(require_auth)):
    for i, account in enumerate(accounts):
        if account.id == account_id:
            _private_tokens.pop(account_id, None)
            removed = accounts.pop(i)
            _delete_account_db(account_id)
            return {"deleted": True, "account": removed}
    raise HTTPException(status_code=404, detail="Account not found")


@app.put("/accounts/{account_id}", response_model=Account)
def update_account(account_id: int, payload: AccountCreate, user=Depends(require_auth)):
    for i, account in enumerate(accounts):
        if account.id == account_id:
            updated = Account(id=account_id, platform=payload.platform, name=payload.name, status=payload.status, token_saved=account.token_saved or bool(payload.access_token))
            if payload.access_token:
                _private_tokens[account_id] = payload.access_token
            accounts[i] = updated
            _save_account(updated, payload.access_token)
            return updated
    raise HTTPException(status_code=404, detail="Account not found")

@app.get("/settings", response_model=Settings)
def get_settings(user=Depends(require_auth)):
    return settings

@app.put("/settings", response_model=Settings)
def update_settings(payload: Settings, user=Depends(require_auth)):
    global settings
    settings = payload
    _save_settings(settings)
    return settings

@app.get("/posts/export")
def export_posts(user=Depends(require_auth)):
    return [p.model_dump(mode="json") for p in posts]

@app.post("/posts/reset")
def reset_posts(user=Depends(require_auth)):
    """Clear all posts. Kept for admin cleanup; no demo data is restored."""
    global posts, next_post_id
    posts = []
    next_post_id = 1
    _replace_all_posts(posts)
    return {"ok": True, "count": 0}

@app.post("/demo/seed")
def seed_demo_content(replace: bool = False, user=Depends(require_auth)):
    """Add sample posts/accounts for presentation testing. No real tokens are stored."""
    result = _seed_demo_content(replace=replace)
    return {"ok": True, **result}

@app.get("/previews", response_model=list[Post])
def get_previews(platform: Optional[str] = None, saved_only: bool = False, user=Depends(require_auth)):
    data = sorted(posts, key=lambda p: p.scheduled_at, reverse=True)
    if platform and platform != "All":
        data = [p for p in data if p.platform == platform]
    if saved_only:
        data = [p for p in data if p.is_saved]
    return data

@app.patch("/posts/{post_id}/preference", response_model=Post)
def save_post_preference(post_id: int, payload: PreferenceUpdate, user=Depends(require_auth)):
    for i, post in enumerate(posts):
        if post.id == post_id:
            updated = post.model_copy(update={"is_saved": payload.is_saved, "preference_notes": payload.preference_notes})
            posts[i] = updated
            _save_post(updated)
            return updated
    raise HTTPException(status_code=404, detail="Post not found")

@app.post("/posts/{post_id}/feedback", response_model=FeedbackRecord)
def post_feedback(post_id: int, payload: FeedbackCreate, user=Depends(require_auth)):
    feedback = payload.feedback.lower().strip()
    if feedback not in {"like", "dislike"}:
        raise HTTPException(status_code=400, detail="Feedback must be like or dislike")
    for i, post in enumerate(posts):
        if post.id == post_id:
            update = {"like_count": post.like_count + (1 if feedback == "like" else 0), "dislike_count": post.dislike_count + (1 if feedback == "dislike" else 0)}
            updated = post.model_copy(update=update)
            posts[i] = updated
            _save_post(updated)
            feedback_id, created_at = _record_feedback(updated, feedback, payload.reason)
            return FeedbackRecord(id=feedback_id, post_id=post_id, feedback=feedback, reason=payload.reason, created_at=created_at, post_title=updated.title, platform=updated.platform, post_type=updated.post_type)
    raise HTTPException(status_code=404, detail="Post not found")

@app.get("/feedback/training", response_model=list[FeedbackRecord])
def feedback_training(user=Depends(require_auth)):
    with _db() as conn:
        rows = conn.execute("SELECT id, post_id, feedback, reason, created_at, post_snapshot FROM feedback ORDER BY id DESC").fetchall()
    out = []
    for r in rows:
        snap = json.loads(r["post_snapshot"])
        out.append(FeedbackRecord(id=r["id"], post_id=r["post_id"], feedback=r["feedback"], reason=r["reason"], created_at=datetime.fromisoformat(r["created_at"]), post_title=snap.get("title"), platform=snap.get("platform"), post_type=snap.get("post_type")))
    return out


DATASET_PATH = Path(__file__).resolve().parent.parent / "data" / "social_media_engagement1.csv"
_ai_rows_cache: list[dict] | None = None


def _parse_hour(value: str) -> int | None:
    if not value:
        return None
    value = str(value).strip()
    for fmt in ("%m/%d/%Y %H:%M", "%m-%d-%Y %H:%M", "%d-%m-%Y %H:%M", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(value, fmt).hour
        except ValueError:
            pass
    try:
        return datetime.fromisoformat(value).hour
    except Exception:
        return None


def _load_ai_rows() -> list[dict]:
    """Load Kaggle CSV data and create clean AI training rows.
    This lightweight model uses your downloaded dataset directly, so no extra ML install is needed.
    """
    global _ai_rows_cache
    if _ai_rows_cache is not None:
        return _ai_rows_cache
    rows: list[dict] = []
    if DATASET_PATH.exists():
        with DATASET_PATH.open("r", encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                try:
                    likes = int(float(row.get("likes", 0) or 0))
                    comments = int(float(row.get("comments", 0) or 0))
                    shares = int(float(row.get("shares", 0) or 0))
                except ValueError:
                    continue
                hour = _parse_hour(row.get("post_time", ""))
                if hour is None:
                    continue
                rows.append({
                    "platform": (row.get("platform") or "").strip().lower(),
                    "post_type": (row.get("post_type") or "").strip().lower(),
                    "post_day": (row.get("post_day") or "").strip().lower(),
                    "sentiment_score": (row.get("sentiment_score") or "neutral").strip().lower(),
                    "hour": hour,
                    "engagement": likes + comments + shares,
                    "likes": likes,
                    "comments": comments,
                    "shares": shares,
                })
    _ai_rows_cache = rows
    return rows


def _avg(items: list[int | float]) -> float:
    return sum(items) / len(items) if items else 0.0


def _score_percentile(value: int | float) -> int:
    """Convert raw predicted engagement into a readable 0-100 AI score."""
    rows = _load_ai_rows()
    values = sorted([r["engagement"] for r in rows])
    if not values:
        return 50
    below = sum(1 for v in values if v <= value)
    percentile = below / len(values)
    # Keep scores realistic: avoid always showing 0 or 100.
    return max(10, min(98, int(round(percentile * 100))))


def _caption_score(content: str = "", occasion: str = "") -> int:
    text = (content or "").strip()
    length = len(text)
    hashtags = text.count("#")
    score = 45
    if 60 <= length <= 240:
        score += 22
    elif 25 <= length < 60 or 240 < length <= 420:
        score += 12
    if 2 <= hashtags <= 8:
        score += 15
    elif hashtags == 1 or 9 <= hashtags <= 12:
        score += 7
    cta_words = ["shop", "save", "comment", "share", "dm", "message", "follow", "click", "visit", "book", "order"]
    if any(w in text.lower() for w in cta_words):
        score += 10
    if occasion and occasion.lower() not in ("general", ""):
        score += 8
    return max(10, min(100, score))


def _final_ai_score(predicted_engagement: int, content: str = "", occasion: str = "", media_score: int | None = None) -> dict:
    timing = _score_percentile(predicted_engagement)
    caption = _caption_score(content, occasion)
    if media_score is None:
        final = round((timing * 0.72) + (caption * 0.28))
        formula = "72% timing + 28% caption"
    else:
        media_score = max(0, min(100, int(media_score)))
        final = round((timing * 0.55) + (caption * 0.25) + (media_score * 0.20))
        formula = "55% timing + 25% caption + 20% media"
    label = "High" if final >= 75 else "Medium" if final >= 50 else "Low"
    return {"ai_score": max(0, min(100, final)), "timing_score": timing, "caption_score": caption, "media_score": media_score, "score_label": label, "score_formula": formula}


def _analyze_media_file(path: Path, content_type: str = "") -> dict:
    suffix = path.suffix.lower()
    size_mb = path.stat().st_size / (1024 * 1024)
    media_type = "video" if content_type.startswith("video") or suffix in [".mp4", ".mov", ".avi", ".webm"] else "image"
    factors = []
    if media_type == "image" and Image is not None:
        try:
            with Image.open(path) as img:
                img = img.convert("RGB")
                w, h = img.size
                stat = ImageStat.Stat(img)
                brightness = sum(stat.mean) / 3
                contrast = sum(stat.stddev) / 3
                resolution_score = min(100, int((w * h) / (1080 * 1080) * 100))
                brightness_score = max(0, min(100, int(100 - abs(brightness - 135) * 0.75)))
                contrast_score = max(0, min(100, int(contrast * 2.2)))
                aspect = w / max(h, 1)
                aspect_score = 100 if 0.75 <= aspect <= 1.91 else 72
                score = round((resolution_score * 0.30) + (brightness_score * 0.30) + (contrast_score * 0.25) + (aspect_score * 0.15))
                factors = [
                    f"Resolution {w}x{h}",
                    f"Brightness score {brightness_score}/100",
                    f"Contrast score {contrast_score}/100",
                    f"Aspect score {aspect_score}/100",
                ]
                return {"media_type": "image", "media_score": max(10, min(100, score)), "factors": factors}
        except Exception:
            pass
    # Lightweight video/fallback scoring without heavy processing.
    size_score = 85 if 1 <= size_mb <= 80 else 65 if size_mb < 1 else 72
    factors = [f"File size {size_mb:.2f} MB", "Advanced frame analysis not enabled in lightweight mode"]
    return {"media_type": media_type, "media_score": size_score, "factors": factors}


def _matching_score(row: dict, platform: str, post_type: str, post_day: str | None, hour: int | None) -> int:
    score = 0
    if row["platform"] == platform:
        score += 4
    if row["post_type"] == post_type:
        score += 3
    if post_day and row["post_day"] == post_day:
        score += 2
    if hour is not None and row["hour"] == hour:
        score += 2
    return score


def _predict_engagement(platform: str, post_type: str, post_day: str | None = None, hour: int | None = None):
    rows = _load_ai_rows()
    platform = (platform or "instagram").lower()
    post_type = (post_type or "image").lower()
    post_day = (post_day or "").lower() or None
    if not rows:
        return {"predicted_engagement": 0, "confidence": "No dataset", "matched_rows": 0}

    # weighted nearest-neighbour average over historical Kaggle rows
    weighted_total = 0.0
    weight_sum = 0.0
    matched = 0
    for r in rows:
        s = _matching_score(r, platform, post_type, post_day, hour)
        if s > 0:
            weighted_total += r["engagement"] * s
            weight_sum += s
            matched += 1
    if weight_sum == 0:
        return {"predicted_engagement": int(_avg([r["engagement"] for r in rows])), "confidence": "Low", "matched_rows": len(rows)}
    exact = [r for r in rows if r["platform"] == platform and r["post_type"] == post_type and (not post_day or r["post_day"] == post_day) and (hour is None or r["hour"] == hour)]
    confidence = "High" if len(exact) >= 3 else "Medium" if matched >= 10 else "Low"
    return {"predicted_engagement": int(round(weighted_total / weight_sum)), "confidence": confidence, "matched_rows": matched}


def _hashtags(platform: str, post_type: str, occasion: str = ""):
    base = ["#SocialMedia", "#Marketing", "#Growth"]
    p = (platform or "").lower()
    t = (post_type or "").lower()
    if p == "instagram": base += ["#InstagramMarketing", "#Reels", "#InstaGrowth"]
    if p == "facebook": base += ["#FacebookMarketing", "#Community", "#BrandPost"]
    if p == "twitter": base += ["#TwitterMarketing", "#Thread", "#Trending"]
    if p == "linkedin": base += ["#LinkedInMarketing", "#Business", "#ProfessionalGrowth"]
    if "sale" in occasion.lower() or "launch" in occasion.lower(): base += ["#NewLaunch", "#Offer"]
    if t == "video": base += ["#VideoContent"]
    if t == "carousel": base += ["#CarouselPost"]
    return list(dict.fromkeys(base))[:8]

@app.post("/media/analyze")
async def media_analyze(file: UploadFile = File(...), user=Depends(require_auth)):
    safe_name = Path(file.filename or "upload.bin").name.replace(" ", "_")
    unique = f"{int(datetime.utcnow().timestamp())}_{secrets.token_hex(4)}_{safe_name}"
    dest = UPLOAD_DIR / unique
    with dest.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    analysis = _analyze_media_file(dest, file.content_type or "")
    return {
        "filename": unique,
        "media_url": f"/uploads/{unique}",
        "media_type": analysis["media_type"],
        "media_score": analysis["media_score"],
        "factors": analysis["factors"],
        "message": "Media analyzed successfully. Combine this with timing score for a better AI score."
    }

@app.post("/ai/caption")
def generate_caption(data: dict, user=Depends(require_auth)):
    topic = data.get("topic") or "your product"
    platform = data.get("platform") or "social media"
    return {"caption": f"Stop scrolling — {topic} is here. A fresh update made for {platform}, with a simple hook, useful value, and a clear call to action. Save this post and message us to know more. #Marketing #Growth #SocialMedia"}

@app.post("/ai/predict")
def ai_predict(data: dict, user=Depends(require_auth)):
    platform = data.get("platform", "Instagram")
    post_type = data.get("post_type", "image")
    post_day = data.get("post_day")
    hour = data.get("hour")
    try:
        hour = int(hour) if hour is not None and hour != "" else None
    except Exception:
        hour = None
    result = _predict_engagement(platform, post_type, post_day, hour)
    score = _final_ai_score(
        result["predicted_engagement"],
        content=data.get("content", ""),
        occasion=data.get("occasion", ""),
        media_score=data.get("media_score"),
    )
    preference_bonus = _feedback_bonus(platform, post_type)
    if preference_bonus:
        score["ai_score"] = max(0, min(100, score["ai_score"] + preference_bonus))
        score["preference_bonus"] = preference_bonus
    result.update(score)
    result["hashtags"] = _hashtags(platform, post_type, data.get("occasion", ""))
    result["model"] = "Kaggle engagement dataset + caption/media scoring"
    result["message"] = "AI score is normalized to 0-100, not raw likes."
    return result

@app.post("/ai/best-time")
def ai_best_time(data: dict, user=Depends(require_auth)):
    platform = data.get("platform", "Instagram")
    post_type = data.get("post_type", "image")
    post_day = data.get("post_day") or data.get("day")
    occasion = data.get("occasion", "")
    scored = []
    for h in range(24):
        pred = _predict_engagement(platform, post_type, post_day, h)
        final = _final_ai_score(pred["predicted_engagement"], data.get("content", ""), occasion, data.get("media_score"))
        preference_bonus = _feedback_bonus(platform, post_type)
        final_score = max(0, min(100, final["ai_score"] + preference_bonus))
        scored.append({"hour": h, "time": f"{h:02d}:00", "score": pred["predicted_engagement"], "ai_score": final_score, "confidence": pred["confidence"], "preference_bonus": preference_bonus})
    scored.sort(key=lambda x: x["ai_score"], reverse=True)
    best = scored[0] if scored else {"hour": 10, "time": "10:00", "score": 0, "confidence": "Low"}
    return {
        "best_time": best["time"],
        "best_hour": best["hour"],
        "predicted_engagement": best["score"],
        "ai_score": best.get("ai_score", _score_percentile(best["score"])),
        "confidence": best["confidence"],
        "top_times": scored[:3],
        "hashtags": _hashtags(platform, post_type, occasion),
        "training_rows": len(_load_ai_rows()),
        "message": "Suggestion generated from Kaggle engagement data, caption quality, and optional media analysis."
    }

@app.post("/ai/ideas")
def generate_ideas(data: dict, user=Depends(require_auth)):
    topic = data.get("topic") or "your business"
    return {"ideas": [
        f"Behind-the-scenes story about {topic}",
        f"Customer problem + solution post for {topic}",
        f"Before/after carousel showing results from {topic}",
        f"Quick educational reel: 3 tips about {topic}",
    ]}

def _dataset_analytics():
    rows = _load_ai_rows()
    if not rows:
        return {
            "total_training_rows": 0,
            "total_likes": 0,
            "total_comments": 0,
            "total_shares": 0,
            "avg_engagement": 0,
            "best_platform": "N/A",
            "best_post_type": "N/A",
            "best_time": "N/A",
            "platform_breakdown": [],
            "post_type_breakdown": [],
            "top_times": [],
        }

    def grouped_average(key):
        groups: dict[str, list[dict]] = {}
        for r in rows:
            groups.setdefault(str(r.get(key, "unknown")).title(), []).append(r)
        out = []
        for name, items in groups.items():
            out.append({
                "name": name,
                "rows": len(items),
                "avg_engagement": int(round(_avg([i["engagement"] for i in items]))),
                "likes": int(sum(i["likes"] for i in items)),
                "comments": int(sum(i["comments"] for i in items)),
                "shares": int(sum(i["shares"] for i in items)),
            })
        return sorted(out, key=lambda x: x["avg_engagement"], reverse=True)

    platform_breakdown = grouped_average("platform")
    post_type_breakdown = grouped_average("post_type")

    hour_groups: dict[int, list[dict]] = {}
    for r in rows:
        hour_groups.setdefault(int(r["hour"]), []).append(r)
    top_times = sorted([
        {"hour": h, "time": f"{h:02d}:00", "avg_engagement": int(round(_avg([i["engagement"] for i in items]))), "rows": len(items)}
        for h, items in hour_groups.items()
    ], key=lambda x: x["avg_engagement"], reverse=True)[:5]

    return {
        "total_training_rows": len(rows),
        "total_likes": int(sum(r["likes"] for r in rows)),
        "total_comments": int(sum(r["comments"] for r in rows)),
        "total_shares": int(sum(r["shares"] for r in rows)),
        "avg_engagement": int(round(_avg([r["engagement"] for r in rows]))),
        "best_platform": platform_breakdown[0]["name"] if platform_breakdown else "N/A",
        "best_post_type": post_type_breakdown[0]["name"] if post_type_breakdown else "N/A",
        "best_time": top_times[0]["time"] if top_times else "N/A",
        "platform_breakdown": platform_breakdown,
        "post_type_breakdown": post_type_breakdown,
        "top_times": top_times,
    }

@app.get("/analytics/summary")
def analytics_summary(user=Depends(require_auth)):
    dataset = _dataset_analytics()
    scheduled = len([p for p in posts if p.status.lower() == "scheduled"])
    posted = len([p for p in posts if p.status.lower() == "posted"])
    drafts = len([p for p in posts if p.status.lower() in {"draft", "drafting", "idea"}])
    return {
        "cards": {
            "training_rows": dataset["total_training_rows"],
            "avg_engagement": dataset["avg_engagement"],
            "scheduled_posts": scheduled,
            "draft_posts": drafts,
            "posted_posts": posted,
            "connected_accounts": len(accounts),
            "best_platform": dataset["best_platform"],
            "best_post_type": dataset["best_post_type"],
            "best_time": dataset["best_time"],
        },
        "dataset": dataset,
        "app": {
            "total_posts": len(posts),
            "scheduled": scheduled,
            "drafts": drafts,
            "posted": posted,
            "connected_accounts": len(accounts),
        },
        "message": "Analytics are calculated from your Kaggle training CSV plus your scheduled posts."
    }

@app.get("/ai/insights")
def ai_insights(user=Depends(require_auth)):
    dataset = _dataset_analytics()
    platform_rows = dataset["platform_breakdown"]
    type_rows = dataset["post_type_breakdown"]
    time_rows = dataset["top_times"]

    best_platform = platform_rows[0] if platform_rows else {"name": "Instagram", "avg_engagement": 0}
    best_type = type_rows[0] if type_rows else {"name": "Video", "avg_engagement": 0}
    best_time = time_rows[0] if time_rows else {"time": "10:00", "avg_engagement": 0}
    second_time = time_rows[1] if len(time_rows) > 1 else None

    scheduled_by_platform: dict[str, int] = {}
    for p in posts:
        scheduled_by_platform[p.platform] = scheduled_by_platform.get(p.platform, 0) + 1

    recommendations = [
        f"Prioritize {best_platform['name']} because it has the highest average engagement in the training dataset.",
        f"Use more {best_type['name']} posts; this format has the strongest historical performance.",
        f"Schedule important posts around {best_time['time']} for the strongest predicted engagement.",
    ]
    if second_time:
        recommendations.append(f"Backup posting window: {second_time['time']} also performs well.")
    if scheduled_by_platform:
        most_scheduled = max(scheduled_by_platform, key=scheduled_by_platform.get)
        if most_scheduled.lower() != best_platform["name"].lower():
            recommendations.append(f"Your calendar currently uses {most_scheduled} most, but AI suggests testing more {best_platform['name']} content.")
    else:
        recommendations.append("Create a few scheduled posts first so AI can compare your calendar plan against the training dataset.")

    risks = []
    if dataset["total_training_rows"] < 500:
        risks.append("Training dataset is small, so treat predictions as planning guidance, not guaranteed results.")
    if not any(p.status.lower() == "posted" for p in posts):
        risks.append("No real posted performance is stored yet. Accuracy will improve once you add your own post results.")

    return {
        "recommendations": recommendations,
        "risks": risks,
        "best_platform": best_platform,
        "best_post_type": best_type,
        "best_time": best_time,
        "top_times": time_rows,
        "platform_breakdown": platform_rows,
        "post_type_breakdown": type_rows,
        "model": "Kaggle engagement dataset nearest-neighbour predictor",
        "training_rows": dataset["total_training_rows"],
    }

ADMIN_CSS = """
<style>
*{box-sizing:border-box} body{margin:0;background:#20211f;color:#eee;font-family:Inter,Segoe UI,Arial,sans-serif}.wrap{display:flex;min-height:100vh}.side{width:220px;background:#1d1e1c;border-right:1px solid #3c3d39;padding:18px}.brand{font-size:20px;font-weight:900}.brand span{color:#f1c35b}.muted{color:#a9a49a;font-size:12px}.nav a{display:block;color:#eee;text-decoration:none;margin:14px 0;padding:10px;border-radius:10px}.nav a:hover,.nav .active{background:#2d2e2b}.main{flex:1;padding:24px}.top{display:flex;justify-content:space-between;align-items:center;margin-bottom:18px}.card{background:#292a27;border:1px solid #494a45;border-radius:16px;padding:18px;margin-bottom:16px}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px}.stat strong{display:block;font-size:28px;margin-top:6px}table{width:100%;border-collapse:collapse}td,th{border-bottom:1px solid #454640;padding:10px;text-align:left}input,select,textarea{width:100%;padding:10px;margin:6px 0 12px;background:#1f201e;border:1px solid #4b4c47;border-radius:9px;color:#fff}button,.btn{background:#e8e0ca;color:#1e1f1d;border:0;border-radius:9px;padding:10px 14px;font-weight:800;text-decoration:none;cursor:pointer}.danger{background:#513232;color:#ffd8d8}.login{max-width:380px;margin:12vh auto}.pill{font-size:12px;border:1px solid #575852;border-radius:999px;padding:4px 8px}.ok{color:#bdeedb}.warn{color:#ffe0a4}.row{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px}.api-list{display:grid;gap:10px}.api-row{display:grid;grid-template-columns:90px 210px 1fr;gap:12px;align-items:center;background:#20211f;border:1px solid #454640;border-radius:12px;padding:12px}.method{display:inline-block;text-align:center;border-radius:8px;padding:6px 8px}.get{background:#153b63;color:#9ccaff}.post{background:#164d35;color:#a8f1cc}.put{background:#5a4119;color:#ffd79a}.delete{background:#5a2222;color:#ffb1b1}code{color:#e8e0ca}
</style>
"""

def admin_shell(content: str, active: str = "dashboard"):
    return HTMLResponse(f"""<!doctype html><html><head><title>SocialMedia Admin</title>{ADMIN_CSS}</head><body><div class='wrap'><aside class='side'><div class='brand'>SocialMedia <span>AI</span></div><p class='muted'>Backend Admin Panel</p><div class='nav'><a class='{ 'active' if active=='dashboard' else '' }' href='/admin'>Dashboard</a><a class='{ 'active' if active=='posts' else '' }' href='/admin/posts'>Posts</a><a class='{ 'active' if active=='accounts' else '' }' href='/admin/accounts'>Accounts</a><a class='{ 'active' if active=='docs' else '' }' href='/docs'>API UI</a><a href='/swagger'>Swagger</a><a href='/admin/logout'>Logout</a></div><p class='muted'>Tokens are hidden. API URL is configured through environment variables.</p></aside><main class='main'>{content}</main></div></body></html>""")

@app.get("/admin", response_class=HTMLResponse)
def admin_dashboard(request: Request):
    if not check_cookie(request):
        return RedirectResponse("/admin/login", status_code=302)
    content = f"""<div class='top'><h1>Backend Dashboard</h1><span class='pill ok'>Production clean mode</span></div><div class='grid'><div class='card stat'><span>Total posts</span><strong>{len(posts)}</strong></div><div class='card stat'><span>Connected accounts</span><strong>{len(accounts)}</strong></div><div class='card stat'><span>Saved tokens</span><strong>{len(_private_tokens)}</strong></div><div class='card stat'><span>API UI</span><strong>/docs</strong></div></div><div class='card'><h2>Security</h2><p>No access tokens are shown in the frontend or backend UI. Account tokens are saved privately on the server and displayed only as <b>Saved</b> or <b>Not saved</b>.</p><p class='muted'>Login credentials are loaded only from environment variables. Set ADMIN_EMAIL, ADMIN_PASSWORD and SECRET_KEY in Railway variables before deployment.</p></div>"""
    return admin_shell(content)

@app.get("/admin/login", response_class=HTMLResponse)
def admin_login_page():
    return HTMLResponse(f"""<!doctype html><html><head><title>Admin Login</title>{ADMIN_CSS}</head><body><div class='login card'><h1>SocialMedia Admin</h1><p class='muted'>Login to manage backend data safely.</p><form method='post' action='/admin/login'><label>Email</label><input name='email' placeholder='admin@example.com'><label>Password</label><input name='password' type='password' placeholder='Password from Railway variables'><button>Login</button></form></div></body></html>""")

@app.post("/admin/login")
async def admin_login(request: Request):
    # Parse the HTML form manually so admin login does not depend on python-multipart.
    from urllib.parse import parse_qs

    raw_body = (await request.body()).decode("utf-8")
    form = {k: v[0] for k, v in parse_qs(raw_body).items()}

    require_configured_auth()
    if form.get("email", "").lower().strip() == ADMIN_EMAIL.lower() and form.get("password") == ADMIN_PASSWORD:
        response = RedirectResponse("/admin", status_code=302)
        response.set_cookie("sm_admin_token", create_session(), httponly=True, samesite="lax", max_age=43200)
        return response

    return HTMLResponse(f"{ADMIN_CSS}<div class='login card'><h1>Login failed</h1><p>Wrong email or password.</p><a class='btn' href='/admin/login'>Try again</a></div>", status_code=401)

@app.get("/docs", response_class=HTMLResponse)
def custom_api_ui(request: Request):
    if not check_cookie(request):
        return RedirectResponse("/admin/login", status_code=302)
    endpoints = [
        ("POST", "/auth/login", "Login and receive a bearer session token."),
        ("GET", "/auth/me", "Check the logged-in admin."),
        ("GET", "/posts", "List scheduled posts with optional month/year filters."),
        ("POST", "/posts", "Create a scheduled post."),
        ("PUT", "/posts/{post_id}", "Update an existing post."),
        ("DELETE", "/posts/{post_id}", "Delete a scheduled post."),
        ("GET", "/accounts", "List accounts without exposing tokens."),
        ("POST", "/accounts", "Create/connect an account. Token is saved privately."),
        ("DELETE", "/accounts/{account_id}", "Remove account and saved token."),
        ("POST", "/ai/caption", "Generate a caption."),
        ("POST", "/ai/predict", "Predict engagement using Kaggle dataset."),
        ("POST", "/ai/best-time", "Suggest best posting time from Kaggle dataset."),
        ("POST", "/ai/ideas", "Generate content ideas."),
        ("GET", "/analytics/summary", "View analytics summary."),
    ]
    rows = ''.join([f"<div class='api-row'><b class='method {m.lower()}'>{m}</b><code>{path}</code><span>{desc}</span></div>" for m, path, desc in endpoints])
    content = f"""
    <div class='top'><div><h1>API Control UI</h1><p class='muted'>Cleaner backend API page. Sensitive tokens are not displayed.</p></div><a class='btn' href='/swagger'>Open Swagger</a></div>
    <div class='grid'><div class='card stat'><span>Posts</span><strong>/posts</strong></div><div class='card stat'><span>Accounts</span><strong>/accounts</strong></div><div class='card stat'><span>Auth</span><strong>Protected</strong></div></div>
    <div class='card'><h2>Create Account from Backend</h2><p class='muted'>Token input is hidden and never shown after saving.</p><form method='post' action='/admin/accounts/create' class='row'><label>Platform<select name='platform'><option>Instagram</option><option>Facebook</option><option>LinkedIn</option><option>Twitter</option></select></label><label>Account name<input name='name' placeholder='Aum Creations' required></label><label>Access token<input name='access_token' type='password' placeholder='Paste token, hidden after saving'></label><label>&nbsp;<button>Create Account</button></label></form></div>
    <div class='card'><h2>Available API Routes</h2><div class='api-list'>{rows}</div></div>
    """
    return admin_shell(content, "docs")

@app.post("/admin/accounts/create")
async def admin_create_account(request: Request):
    if not check_cookie(request):
        return RedirectResponse("/admin/login", status_code=302)
    from urllib.parse import parse_qs
    global next_account_id
    raw_body = (await request.body()).decode("utf-8")
    form = {k: v[0] for k, v in parse_qs(raw_body).items()}
    account = Account(id=next_account_id, platform=form.get("platform", "Instagram"), name=form.get("name", "New Account"), token_saved=bool(form.get("access_token")))
    if form.get("access_token"):
        _private_tokens[next_account_id] = form.get("access_token")
    next_account_id += 1
    accounts.append(account)
    _save_account(account, form.get("access_token"))
    return RedirectResponse("/admin/accounts", status_code=302)

@app.get("/admin/logout")
def admin_logout():
    response = RedirectResponse("/admin/login", status_code=302)
    response.delete_cookie("sm_admin_token")
    return response

@app.get("/admin/posts", response_class=HTMLResponse)
def admin_posts(request: Request):
    if not check_cookie(request):
        return RedirectResponse("/admin/login", status_code=302)
    rows = "".join([f"<tr><td>{p.id}</td><td>{p.title}</td><td>{p.platform}</td><td>{p.scheduled_at.strftime('%d %b %Y, %I:%M %p')}</td><td>{p.status}</td></tr>" for p in posts])
    content = f"<div class='top'><h1>Posts</h1><a class='btn' href='/admin'>Back</a></div><div class='card'><table><tr><th>ID</th><th>Title</th><th>Platform</th><th>Schedule</th><th>Status</th></tr>{rows}</table></div>"
    return admin_shell(content, "posts")

@app.get("/admin/accounts", response_class=HTMLResponse)
def admin_accounts(request: Request):
    if not check_cookie(request):
        return RedirectResponse("/admin/login", status_code=302)
    rows = "".join([f"<tr><td>{a.id}</td><td>{a.name}</td><td>{a.platform}</td><td>{a.status}</td><td>{'Saved, hidden' if a.token_saved else 'Not saved'}</td></tr>" for a in accounts])
    content = f"<div class='top'><h1>Accounts</h1><a class='btn' href='/admin'>Back</a></div><div class='card'><table><tr><th>ID</th><th>Name</th><th>Platform</th><th>Status</th><th>Token</th></tr>{rows}</table></div>"
    return admin_shell(content, "accounts")

# --- OAuth starter endpoints for real channel connection testing ---

@app.get("/oauth/meta/config")
def oauth_meta_config():
    app_id = os.getenv("META_APP_ID", "").strip()
    return {
        "configured": bool(app_id),
        "app_id_present": bool(app_id),
        "start_url": "/oauth/meta/start",
        "redirect_uri": os.getenv("META_REDIRECT_URI", "http://localhost:8000/oauth/meta/callback"),
        "scopes": os.getenv("META_SCOPES", "instagram_basic,instagram_content_publish,pages_show_list,pages_read_engagement"),
    }

@app.get("/oauth/meta/start")
def oauth_meta_start():
    """Start Meta OAuth. Configure META_APP_ID, META_APP_SECRET and META_REDIRECT_URI in backend .env."""
    app_id = os.getenv("META_APP_ID", "").strip()
    redirect_uri = os.getenv("META_REDIRECT_URI", "http://localhost:8000/oauth/meta/callback")
    scope = os.getenv("META_SCOPES", "instagram_basic,instagram_content_publish,pages_show_list,pages_read_engagement")
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")
    if not app_id:
        return RedirectResponse(f"{frontend_url}?oauth=missing_meta_app_id")
    params = urlencode({"client_id": app_id, "redirect_uri": redirect_uri, "scope": scope, "response_type": "code"})
    graph_version = os.getenv("META_GRAPH_VERSION", "v19.0")
    return RedirectResponse(f"https://www.facebook.com/{graph_version}/dialog/oauth?{params}")

@app.get("/oauth/meta/callback")
def oauth_meta_callback(code: str = "", error: str = ""):
    """Exchange Meta OAuth code for a token when credentials are configured, then save a channel.

    This keeps secrets server-side. In demo mode, it still redirects cleanly and tells the frontend
    whether the app is missing Meta credentials.
    """
    global next_account_id
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")
    if error:
        return RedirectResponse(f"{frontend_url}?oauth=error")
    if not code:
        return RedirectResponse(f"{frontend_url}?oauth=missing_code")

    app_id = os.getenv("META_APP_ID", "").strip()
    app_secret = os.getenv("META_APP_SECRET", "").strip()
    redirect_uri = os.getenv("META_REDIRECT_URI", "http://localhost:8000/oauth/meta/callback")
    graph_version = os.getenv("META_GRAPH_VERSION", "v19.0")
    if not app_id or not app_secret:
        return RedirectResponse(f"{frontend_url}?oauth=code_received_missing_secret")

    try:
        params = urlencode({"client_id": app_id, "client_secret": app_secret, "redirect_uri": redirect_uri, "code": code})
        with urlopen(f"https://graph.facebook.com/{graph_version}/oauth/access_token?{params}", timeout=15) as resp:
            token_data = json.loads(resp.read().decode("utf-8"))
        access_token = token_data.get("access_token")
        if not access_token:
            return RedirectResponse(f"{frontend_url}?oauth=no_access_token")
        account = Account(id=next_account_id, platform="Instagram", name="Meta connected account", status="Connected", token_saved=True)
        _private_tokens[next_account_id] = access_token
        next_account_id += 1
        accounts.append(account)
        _save_account(account, access_token)
        return RedirectResponse(f"{frontend_url}?oauth=success")
    except Exception:
        return RedirectResponse(f"{frontend_url}?oauth=exchange_failed")
