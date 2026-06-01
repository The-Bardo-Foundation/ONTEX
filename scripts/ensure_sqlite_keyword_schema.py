import sqlite3
from pathlib import Path


DB_PATH = Path("ontex.db")


def column_names(conn: sqlite3.Connection, table_name: str) -> set[str]:
    rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    return {row[1] for row in rows}


def main() -> None:
    conn = sqlite3.connect(DB_PATH)
    try:
        # Align legacy SQLite schema with current clinical_trials expectations
        clinical_cols = column_names(conn, "clinical_trials")
        clinical_additions = {
            "ai_relevance_label": "TEXT",
            "ai_relevance_reason": "TEXT",
            "approved_at": "DATETIME",
            "approved_by": "TEXT",
            "previous_approved_at": "DATETIME",
            "previous_approved_by": "TEXT",
            "rejected_at": "DATETIME",
            "rejected_by": "TEXT",
            "reviewer_notes": "TEXT",
            "ingestion_event": "TEXT",
            "previous_official_snapshot": "TEXT",
        }
        for col_name, col_type in clinical_additions.items():
            if col_name not in clinical_cols:
                conn.execute(
                    f"ALTER TABLE clinical_trials ADD COLUMN {col_name} {col_type}"
                )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS search_keywords (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                term VARCHAR NOT NULL UNIQUE,
                is_active BOOLEAN NOT NULL DEFAULT 1,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS ix_search_keywords_term ON search_keywords(term)"
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS trial_keyword_matches (
                nct_id VARCHAR NOT NULL,
                keyword_id INTEGER NOT NULL,
                matched_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (nct_id, keyword_id),
                FOREIGN KEY(keyword_id) REFERENCES search_keywords(id) ON DELETE CASCADE
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS ix_trial_keyword_matches_nct_id ON trial_keyword_matches(nct_id)"
        )

        if "ingestion_runs" in {
            row[0]
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
        }:
            ingestion_cols = column_names(conn, "ingestion_runs")
            ingestion_additions = {
                "relevant_processed": "INTEGER NOT NULL DEFAULT 0",
                "irrelevant_processed": "INTEGER NOT NULL DEFAULT 0",
                "fetch_errors": "INTEGER NOT NULL DEFAULT 0",
                "classify_errors": "INTEGER NOT NULL DEFAULT 0",
                "skipped_unchanged": "INTEGER NOT NULL DEFAULT 0",
                "pruned_trials": "INTEGER NOT NULL DEFAULT 0",
            }
            for col_name, col_type in ingestion_additions.items():
                if col_name not in ingestion_cols:
                    conn.execute(
                        f"ALTER TABLE ingestion_runs ADD COLUMN {col_name} {col_type}"
                    )

        conn.execute(
            """
            INSERT OR IGNORE INTO search_keywords (term, is_active)
            VALUES ('osteosarcoma', 1)
            """
        )
        conn.commit()
    finally:
        conn.close()


if __name__ == "__main__":
    main()
