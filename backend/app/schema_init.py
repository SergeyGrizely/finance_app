from sqlalchemy import inspect, text


def ensure_schema(engine):
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    if "transactions" not in tables:
        return

    columns = {column["name"] for column in inspector.get_columns("transactions")}
    with engine.begin() as conn:
        if "category_id" not in columns:
            conn.execute(text("ALTER TABLE transactions ADD COLUMN category_id INTEGER"))
        if "account_id" not in columns:
            conn.execute(text("ALTER TABLE transactions ADD COLUMN account_id INTEGER"))

        if "category" in columns:
            rows = conn.execute(
                text(
                    """
                    SELECT DISTINCT owner_id, category, type
                    FROM transactions
                    WHERE category IS NOT NULL AND category <> ''
                    """
                )
            ).fetchall()

            for row in rows:
                category_id = conn.execute(
                    text(
                        """
                        SELECT id
                        FROM categories
                        WHERE user_id = :user_id AND name = :name AND type = :type
                        LIMIT 1
                        """
                    ),
                    {"user_id": row.owner_id, "name": row.category, "type": row.type or "expense"},
                ).scalar()

                if category_id is None:
                    category_id = conn.execute(
                        text(
                            """
                            INSERT INTO categories (name, type, user_id)
                            VALUES (:name, :type, :user_id)
                            RETURNING id
                            """
                        ),
                        {"name": row.category, "type": row.type or "expense", "user_id": row.owner_id},
                    ).scalar()

                conn.execute(
                    text(
                        """
                        UPDATE transactions
                        SET category_id = :category_id
                        WHERE owner_id = :user_id
                          AND category = :category_name
                          AND type = :type
                          AND category_id IS NULL
                        """
                    ),
                    {
                        "category_id": category_id,
                        "user_id": row.owner_id,
                        "category_name": row.category,
                        "type": row.type or "expense",
                    },
                )

            uncategorized_rows = conn.execute(
                text(
                    """
                    SELECT DISTINCT owner_id, type
                    FROM transactions
                    WHERE category_id IS NULL
                    """
                )
            ).fetchall()

            for row in uncategorized_rows:
                fallback_name = "Uncategorized income" if row.type == "income" else "Uncategorized expense"
                category_id = conn.execute(
                    text(
                        """
                        SELECT id
                        FROM categories
                        WHERE user_id = :user_id AND name = :name AND type = :type
                        LIMIT 1
                        """
                    ),
                    {"user_id": row.owner_id, "name": fallback_name, "type": row.type},
                ).scalar()
                if category_id is None:
                    category_id = conn.execute(
                        text(
                            """
                            INSERT INTO categories (name, type, user_id)
                            VALUES (:name, :type, :user_id)
                            RETURNING id
                            """
                        ),
                        {"name": fallback_name, "type": row.type, "user_id": row.owner_id},
                    ).scalar()

                conn.execute(
                    text(
                        """
                        UPDATE transactions
                        SET category_id = :category_id
                        WHERE owner_id = :user_id
                          AND type = :type
                          AND category_id IS NULL
                        """
                    ),
                    {"category_id": category_id, "user_id": row.owner_id, "type": row.type},
                )
