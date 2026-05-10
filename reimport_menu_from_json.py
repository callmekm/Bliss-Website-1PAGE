#!/usr/bin/env python3
"""
One-shot: delete all menu rows and import menu_data.json into menu.db.
Run from project root: python3 reimport_menu_from_json.py
"""
import json
import os
import sqlite3
import uuid

DATABASE = "menu.db"
JSON_FILE = "menu_data.json"


def generate_id(text="item"):
    safe_text = text.lower().strip().replace(" ", "_")
    short_uuid = str(uuid.uuid4())[:8]
    return f"{safe_text}_{short_uuid}"


def main():
    root = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(root, DATABASE)
    json_path = os.path.join(root, JSON_FILE)

    if not os.path.isfile(json_path):
        raise SystemExit(f"Missing {JSON_FILE}")

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")

    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS categories (
            id TEXT PRIMARY KEY,
            name_en TEXT NOT NULL,
            name_mk TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS subcategories (
            id TEXT PRIMARY KEY,
            category_id TEXT NOT NULL,
            name_en TEXT NOT NULL,
            name_mk TEXT NOT NULL,
            FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS items (
            id TEXT PRIMARY KEY,
            category_id TEXT,
            subcategory_id TEXT,
            name_en TEXT NOT NULL,
            name_mk TEXT NOT NULL,
            description_en TEXT DEFAULT '',
            description_mk TEXT DEFAULT '',
            price TEXT DEFAULT '',
            image TEXT DEFAULT '',
            featured INTEGER DEFAULT 0,
            FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE,
            FOREIGN KEY (subcategory_id) REFERENCES subcategories(id) ON DELETE CASCADE
        );
        DELETE FROM items;
        DELETE FROM subcategories;
        DELETE FROM categories;
        """
    )

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    for category in data.get("categories", []):
        category_id = category.get("id") or generate_id(
            category.get("name_en", "category")
        )

        conn.execute(
            """
            INSERT INTO categories (id, name_en, name_mk)
            VALUES (?, ?, ?)
            """,
            (
                category_id,
                category.get("name_en", ""),
                category.get("name_mk", ""),
            ),
        )

        for item in category.get("items", []):
            item_id = item.get("id") or generate_id(item.get("name_en", "item"))
            conn.execute(
                """
                INSERT INTO items (
                    id, category_id, subcategory_id,
                    name_en, name_mk, description_en, description_mk,
                    price, image, featured
                )
                VALUES (?, ?, NULL, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    item_id,
                    category_id,
                    item.get("name_en", ""),
                    item.get("name_mk", ""),
                    item.get("description_en", ""),
                    item.get("description_mk", ""),
                    item.get("price", ""),
                    item.get("image", ""),
                    int(bool(item.get("featured", False))),
                ),
            )

        for subcategory in category.get("subcategories", []):
            subcategory_id = subcategory.get("id") or generate_id(
                subcategory.get("name_en", "subcategory")
            )

            conn.execute(
                """
                INSERT INTO subcategories (id, category_id, name_en, name_mk)
                VALUES (?, ?, ?, ?)
                """,
                (
                    subcategory_id,
                    category_id,
                    subcategory.get("name_en", ""),
                    subcategory.get("name_mk", ""),
                ),
            )

            for item in subcategory.get("items", []):
                item_id = item.get("id") or generate_id(item.get("name_en", "item"))
                conn.execute(
                    """
                    INSERT INTO items (
                        id, category_id, subcategory_id,
                        name_en, name_mk, description_en, description_mk,
                        price, image, featured
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        item_id,
                        category_id,
                        subcategory_id,
                        item.get("name_en", ""),
                        item.get("name_mk", ""),
                        item.get("description_en", ""),
                        item.get("description_mk", ""),
                        item.get("price", ""),
                        item.get("image", ""),
                        int(bool(item.get("featured", False))),
                    ),
                )

    conn.commit()
    conn.close()
    print("Imported", JSON_FILE, "into", db_path)


if __name__ == "__main__":
    main()
