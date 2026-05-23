from app import app, db
from sqlalchemy import text, inspect
from datetime import datetime

try:
    from models import Job
except Exception:
    Job = None

SAMPLE_JOBS = [
    {
        "title": "Frontend Developer",
        "company": "Acme Corp",
        "description": "Build and maintain responsive user interfaces.",
        "location": "New York, NY",
        "salary": "$90,000"
    },
    {
        "title": "Backend Engineer",
        "company": "DataWorks",
        "description": "Develop REST APIs and database schemas.",
        "location": "Remote",
        "salary": "$110,000"
    },
    {
        "title": "Full Stack Engineer",
        "company": "Startup Labs",
        "description": "Own features end-to-end from DB to UI.",
        "location": "San Francisco, CA",
        "salary": "$130,000"
    },
    {
        "title": "Data Scientist",
        "company": "InsightAI",
        "description": "Build ML models and data pipelines.",
        "location": "Boston, MA",
        "salary": "$125,000"
    },
    {
        "title": "DevOps Engineer",
        "company": "CloudScale",
        "description": "Improve CI/CD and infrastructure reliability.",
        "location": "Seattle, WA",
        "salary": "$120,000"
    }
]


def seed():
    with app.app_context():
        added = 0
        inspector = inspect(db.engine)
        cols = [c['name'] for c in inspector.get_columns('job')]

        for j in SAMPLE_JOBS:
            # use raw SQL to avoid ORM expecting new columns in older schemas
            exists = db.session.execute(
                text("SELECT id FROM job WHERE title=:title AND company=:company LIMIT 1"),
                {"title": j['title'], "company": j['company']}
            ).first()

            if not exists:
                insert_cols = [c for c in ['title', 'company', 'description', 'location', 'salary', 'created_at'] if c in cols]
                params = {k: j.get(k) for k in insert_cols}
                if 'created_at' in insert_cols:
                    params['created_at'] = datetime.utcnow()

                cols_sql = ', '.join(insert_cols)
                vals_sql = ', '.join([f':{c}' for c in insert_cols])
                sql = text(f"INSERT INTO job ({cols_sql}) VALUES ({vals_sql})")
                db.session.execute(sql, params)
                added += 1
        if added:
            db.session.commit()
        print(f"Seed complete — added {added} new job(s).")


if __name__ == '__main__':
    seed()
