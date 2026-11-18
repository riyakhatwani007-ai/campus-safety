# Campus Safety & AI Emergency Assistance System

Flask + SQLite/MySQL + scikit-learn. Students send an SOS in plain English/Hinglish; the AI triages the
emergency, shows first-aid steps and relevant contacts, and shares live GPS with campus security.

## Setup (Windows, VS Code)

1. Install Python 3.10+ from python.org (tick **Add Python to PATH**).
2. Open this folder in VS Code, then open a terminal (Ctrl + `) and run:
   ```
   python -m venv venv
   venv\Scripts\activate
   pip install -r requirements.txt
   ```
3. Build the dataset and train the model (30 seconds):
   ```
   python data/generate_dataset.py
   python models/train_triage.py
   ```
   Read the printed accuracy and look at the `models/confusion_*.png` images. They go in your report.
4. Run the tests (all 9 should say OK):
   ```
   python -m unittest tests.test_app -v
   ```
5. Start the app:
   ```
   python app.py
   ```
   Open http://localhost:5000

## Accounts
- Register a student account on the Register page.
- Security login: `security@campus.local` / `ChangeMe123`. **Change this** before any real use:
  set the environment variable `SECURITY_PASSWORD` before the very first run, or delete
  `campus_safety.db` and restart.

## Phone testing (GPS needs HTTPS)
Phones only allow GPS on HTTPS pages. Easiest way: install ngrok, run `ngrok http 5000`, and open the
`https://...ngrok-free.app` link on your phone.

## Switching to MySQL (matches your synopsis)
1. `pip install mysql-connector-python`
2. In MySQL: `CREATE DATABASE campus_safety;`
3. Set environment variables, then run `python app.py`:
   `DB_TYPE=mysql DB_USER=root DB_PASSWORD=yourpassword`  (PowerShell: `$env:DB_TYPE="mysql"`)
Tables are created automatically from `schema_mysql.sql`.

## What to edit
| File | What to change |
|---|---|
| `contacts.json` | Replace every `REPLACE-ME` with Career Point's real numbers (delete `campus_safety.db` after editing so it reloads) |
| `data/emergency_data.csv` | Add your own messages (`text,category,severity`), then retrain |
| `data/first_aid.json` | Verify steps against Red Cross / St John / NDMA, then set `"verified": true` |

## Project map
- `app.py` routes, auth, SOS API, dashboard API
- `db.py` + `schema_*.sql` database layer (4 tables)
- `models/triage.py` AI prediction + safety rules; `models/train_triage.py` training + evaluation
- `templates/`, `static/` screens, GPS script, dashboard map
- `tests/test_app.py` automated tests

## Known limits (mention in your report)
- Starter dataset is synthetic; real-world accuracy will differ. Held-out score is printed by the trainer.
- No CSRF tokens or rate limiting (future work). Location tracking runs only while the incident page is open.
- The dashboard map uses OpenStreetMap tiles and needs internet.
