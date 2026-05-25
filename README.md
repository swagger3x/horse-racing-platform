# Horse Racing Platform — Phase 1

A backend data pipeline that ingests horse racing XML feeds, parses them, and stores the data in a structured PostgreSQL database on Supabase.

---

## Project Structure

```
horse-racing-platform/
│
├── audit/
│   └── audit.py          # XML feed audit script — maps all available fields
│
├── database/
│   ├── schema.sql         # Full PostgreSQL schema (CREATE TABLE statements)
│   └── seed.py            # Script to apply schema to Supabase
│
├── pipeline/
│   ├── ingest.py          # Main pipeline entry point (scheduler)
│   ├── parser.py          # XML parsing and data transformation
│   └── db.py              # Database upsert operations
│
├── sample-data/           # Place XML feed files here (not committed to git)
├── docs/                  # Additional documentation
├── .env                   # Credentials (never committed)
├── .gitignore
├── requirements.txt
└── README.md
```

---

## Setup Instructions

### 1. Clone the repository
```bash
git clone https://github.com/yourusername/horse-racing-platform.git
cd horse-racing-platform
```

### 2. Create a virtual environment
```bash
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # Mac/Linux
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure environment variables
```bash
cp .env.example .env
# Edit .env with your Supabase credentials
```

### 5. Apply the database schema
```bash
python database/seed.py
```

### 6. Run the XML audit
```bash
python audit/audit.py --fields sample-data/FLE_FIELDS_XML_A.xml --form sample-data/FLE_FORM_XML_A.xml
```

### 7. Run the pipeline (manual trigger)
```bash
python pipeline/ingest.py --once
```

### 8. Run the pipeline (scheduled)
```bash
python pipeline/ingest.py --schedule
```

---

## Database Overview

| Table | Description |
|---|---|
| meetings | One row per race day per venue |
| races | Individual races within a meeting |
| horses | Permanent horse profiles |
| people | Trainers and jockeys |
| runners | A horse's entry in a specific race |
| past_runs | Historical race results per horse |
| runners_statistics | Win/place stats by condition type |
| runners_ratings | Performance ratings by condition type |

---

## Phase 2 (Planned)

- OpenAI voice-to-text integration
- AI race insights and tips
- Glide frontend connection

---

## Notes

- All XML dates (DD/MM/YYYY) are converted to ISO 8601 on ingestion
- Fractional prices (e.g. 5/4) are stored alongside decimal equivalents
- All upserts use ON CONFLICT DO UPDATE — safe to re-run anytime
- Placeholder columns for AI integration are already in the schema