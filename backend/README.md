# Backend

Run:

```bash
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Backend UI: `http://localhost:8000/admin`
API Docs: `http://localhost:8000/docs`

Default demo login: `admin@socialmedia.ai` / `admin123`

Create `.env` from `.env.example` before real use.
