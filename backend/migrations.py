from sqlalchemy import inspect, text


def run_migrations(engine) -> None:
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS article_qty_carton (
                    art_num TEXT PRIMARY KEY,
                    qty_per_carton INTEGER NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
        )

        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS app_setting (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL DEFAULT '',
                    updated_at TEXT NOT NULL
                )
                """
            )
        )

        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS packlist_session (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    filename TEXT NOT NULL DEFAULT '',
                    imported_at TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'active',
                    warnings_json TEXT NOT NULL DEFAULT '[]'
                )
                """
            )
        )

        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS packlist_line (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER NOT NULL,
                    row_num INTEGER NOT NULL,
                    carton_spec TEXT NOT NULL,
                    stock_code TEXT NOT NULL,
                    total_qty INTEGER NOT NULL,
                    qty_per_carton INTEGER NOT NULL,
                    num_cartons INTEGER NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES packlist_session(id)
                )
                """
            )
        )

        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS packlist_carton_entry (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER NOT NULL,
                    carton_id INTEGER NOT NULL,
                    line_id INTEGER NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES packlist_session(id),
                    FOREIGN KEY (line_id) REFERENCES packlist_line(id),
                    UNIQUE(session_id, carton_id, line_id)
                )
                """
            )
        )

        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS pallet (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER NOT NULL,
                    pallet_num TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    printed_at TEXT,
                    FOREIGN KEY (session_id) REFERENCES packlist_session(id),
                    UNIQUE(session_id, pallet_num)
                )
                """
            )
        )

        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS carton_assignment (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER NOT NULL,
                    carton_id INTEGER NOT NULL,
                    pallet_id INTEGER NOT NULL,
                    scan_text TEXT NOT NULL DEFAULT '',
                    assigned_at TEXT NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES packlist_session(id),
                    FOREIGN KEY (pallet_id) REFERENCES pallet(id),
                    UNIQUE(session_id, carton_id)
                )
                """
            )
        )

        inspector = inspect(engine)
        if "article_qty_carton" in inspector.get_table_names():
            cols = {c["name"] for c in inspector.get_columns("article_qty_carton")}
            if cols != {"art_num", "qty_per_carton", "updated_at"}:
                pass
