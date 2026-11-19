# Email / Document Automation

AI writing assistant for professional emails, letters, applications, reports, and document summarization with PDF/DOCX export and optional SMTP sending.

## Features

- Generate emails, letters, applications, reports, and documents
- Multiple writing tones
- Summarize uploaded PDF and DOCX files
- Extract key information from documents
- Export generated content to PDF and DOCX
- Optional email sending when SMTP credentials are configured

## Setup

```powershell
cd Email_Document_Automation
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

Required in `.env`:

```
OPENROUTER_API_KEY=sk-or-v1-your-real-key
```

Optional SMTP (enables Send email):

```
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your@email.com
SMTP_PASSWORD=your_app_password
SMTP_FROM_EMAIL=your@email.com
SMTP_USE_TLS=true
```

## Run

```powershell
uvicorn backend.main:app --host 0.0.0.0 --port 8004 --reload
```

Open: [http://127.0.0.1:8004](http://127.0.0.1:8004)

## API

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/health` | Health + SMTP status |
| POST | `/api/generate` | Generate document/email |
| POST | `/api/summarize-text` | Summarize raw text |
| POST | `/api/summarize-file` | Summarize PDF/DOCX upload |
| GET | `/api/export/{id}/pdf` | Export PDF |
| GET | `/api/export/{id}/docx` | Export DOCX |
| POST | `/api/send-email` | Send via SMTP |

Port default: **8004**
