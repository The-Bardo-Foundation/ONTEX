<p align="center">
  <img src="https://github.com/user-attachments/assets/fccb203d-3d15-4732-9a6b-45f6de9b8003" height="170" alt="Osteosarcoma Now" style="vertical-align: top;" />
  &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
  <img width="300" height="138" alt="image" src="https://github.com/user-attachments/assets/31383b6b-bdbf-4349-b6bb-081eb3c5fd58" />
</p>

# AI-Augmented Clinical Trial Explorer (ACTE)

ACTE is a modern clinical trial database system for **Osteosarcoma Now**. It replaces legacy infrastructure with an AI-integrated pipeline to provide patients with accessible, up-to-date clinical trial information.

## Core Components
- **Data Ingestion**: Automated daily sync with ClinicalTrials.gov.
- **AI Processing**: AI powered summarization of technical trial data into patient-friendly language.
- **Curation Dashboard**: Human-in-the-loop interface for staff validation and editing.
- **Delivery API**: FastAPI backend for data distribution.

## Tech Stack
- **Backend**: Python, FastAPI, SQLAlchemy, PostgreSQL
- **AI**: OpenAI API (GPT-4)
- **Frontend**: React, TypeScript, Vite, Tailwind CSS

## Quick Setup
For detailed setup, development workflows, and deployment instructions, please refer to the [Development Guide](docs/DEV_GUIDE.md).

```powershell
# Install backend dependencies
pip install -r requirements.txt

# Run migrations
alembic upgrade head

# Start the API
uvicorn app.main:app --reload
```
