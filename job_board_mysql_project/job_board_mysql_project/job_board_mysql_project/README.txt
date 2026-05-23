# Job Board Flask Project (MySQL Version)

## Setup Instructions

1. Install packages

pip install -r requirements.txt

2. Create MySQL database

CREATE DATABASE jobboard_db;

3. Open app.py

Replace:

YOUR_PASSWORD

with your MySQL password.

4. Run project

Windows (PowerShell) - set DB env vars and run:

```powershell
$env:DB_USER='root'; $env:DB_PASS='keerthana2004'; $env:DB_HOST='localhost'; $env:DB_NAME='jobboard_db'; python app.py
```

Or simple run (uses values inside `app.py` if set):

```bash
python app.py
```

5. Open browser

http://127.0.0.1:5000
