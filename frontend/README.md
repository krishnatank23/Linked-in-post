# Frontend UI

Interactive frontend for the LinkedIn Personal Branding Assistant.

## Features

- Separate Register and Login views
- Upload LinkedIn JSON / Resume (PDF, DOCX)
- Optional inputs for past posts and media metadata
- Buttons to run analysis, fetch influencers, generate strategy, and generate posts
- Dynamic non-dark theme generated on every load

## Run

1. Start backend first:

```bash
cd backend
uvicorn app.main:app --reload
```

2. Serve frontend:

```bash
cd frontend
python -m http.server 5500
```

3. Open:

- http://localhost:5500

Default API URL in UI is `http://127.0.0.1:8000`.
