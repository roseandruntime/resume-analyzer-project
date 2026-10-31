"""
Database layer for Resume Analyzer.
Keeps the existing schema and safely adds recruiter-sharing support.
"""
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = BASE_DIR / "resume_analyzer.db"


def get_connection():
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def init_db():
    schema = """
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY AUTOINCREMENT,
        full_name TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE COLLATE NOCASE,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL CHECK (role IN ('student', 'recruiter', 'admin')),
        is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS resumes (
        resume_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        original_filename TEXT NOT NULL,
        stored_file_path TEXT NOT NULL,
        file_type TEXT NOT NULL CHECK (file_type IN ('pdf', 'docx')),
        uploaded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(user_id)
            ON UPDATE CASCADE ON DELETE RESTRICT
    );
    CREATE TABLE IF NOT EXISTS job_descriptions (
        job_id INTEGER PRIMARY KEY AUTOINCREMENT,
        created_by INTEGER NOT NULL,
        job_title TEXT NOT NULL,
        company_name TEXT,
        description_text TEXT NOT NULL,
        required_skills TEXT NOT NULL,
        essential_skills TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (created_by) REFERENCES users(user_id)
            ON UPDATE CASCADE ON DELETE RESTRICT
    );
    CREATE TABLE IF NOT EXISTS analyses (
        analysis_id INTEGER PRIMARY KEY AUTOINCREMENT,
        resume_id INTEGER NOT NULL,
        job_id INTEGER NOT NULL,
        match_score REAL NOT NULL CHECK (match_score >= 0 AND match_score <= 100),
        matched_keywords TEXT NOT NULL,
        missing_keywords TEXT NOT NULL,
        essential_skill_results TEXT NOT NULL,
        formatting_results TEXT NOT NULL,
        suggestions TEXT NOT NULL,
        analyzed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (resume_id) REFERENCES resumes(resume_id)
            ON UPDATE CASCADE ON DELETE RESTRICT,
        FOREIGN KEY (job_id) REFERENCES job_descriptions(job_id)
            ON UPDATE CASCADE ON DELETE RESTRICT
    );
    CREATE TABLE IF NOT EXISTS reports (
        report_id INTEGER PRIMARY KEY AUTOINCREMENT,
        analysis_id INTEGER NOT NULL,
        stored_file_path TEXT NOT NULL,
        generated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (analysis_id) REFERENCES analyses(analysis_id)
            ON UPDATE CASCADE ON DELETE CASCADE
    );
    CREATE TABLE IF NOT EXISTS recruiter_reviews (
        review_id INTEGER PRIMARY KEY AUTOINCREMENT,
        recruiter_id INTEGER NOT NULL,
        analysis_id INTEGER NOT NULL,
        review_comments TEXT NOT NULL DEFAULT '',
        review_status TEXT NOT NULL DEFAULT 'reviewed'
            CHECK (review_status IN ('reviewed', 'shortlisted', 'rejected', 'pending')),
        reviewed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (recruiter_id) REFERENCES users(user_id)
            ON UPDATE CASCADE ON DELETE RESTRICT,
        FOREIGN KEY (analysis_id) REFERENCES analyses(analysis_id)
            ON UPDATE CASCADE ON DELETE CASCADE,
        UNIQUE (recruiter_id, analysis_id)
    );
    CREATE TABLE IF NOT EXISTS system_settings (
        setting_id INTEGER PRIMARY KEY AUTOINCREMENT,
        setting_name TEXT NOT NULL UNIQUE,
        setting_value TEXT NOT NULL,
        updated_by INTEGER,
        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (updated_by) REFERENCES users(user_id)
            ON UPDATE CASCADE ON DELETE SET NULL
    );
    CREATE INDEX IF NOT EXISTS idx_resumes_user_id ON resumes(user_id);
    CREATE INDEX IF NOT EXISTS idx_jobs_created_by ON job_descriptions(created_by);
    CREATE INDEX IF NOT EXISTS idx_analyses_resume_id ON analyses(resume_id);
    CREATE INDEX IF NOT EXISTS idx_analyses_job_id ON analyses(job_id);
    CREATE INDEX IF NOT EXISTS idx_reviews_recruiter_id ON recruiter_reviews(recruiter_id);
    """
    with get_connection() as connection:
        connection.executescript(schema)
        # Backward-compatible migration: old analyses remain private by default.
        columns = {
            row["name"] for row in connection.execute("PRAGMA table_info(analyses)")
        }
        if "shared_with_recruiters" not in columns:
            connection.execute(
                "ALTER TABLE analyses ADD COLUMN shared_with_recruiters INTEGER NOT NULL DEFAULT 0"
            )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_analyses_shared ON analyses(shared_with_recruiters)"
        )
        # Existing databases need this index too for the review UPSERT to work.
        connection.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_reviews_recruiter_analysis "
            "ON recruiter_reviews(recruiter_id, analysis_id)"
        )


if __name__ == "__main__":
    init_db()
    print(f"Database initialized successfully: {DATABASE_PATH}")
