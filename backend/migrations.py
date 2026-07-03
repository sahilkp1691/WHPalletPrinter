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

        inspector = inspect(engine)
        if "article_qty_carton" in inspector.get_table_names():
            cols = {c["name"] for c in inspector.get_columns("article_qty_carton")}
            if cols != {"art_num", "qty_per_carton", "updated_at"}:
                pass
