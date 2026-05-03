from flask import Flask, render_template, redirect, request, url_for, session, jsonify
from functools import wraps
from werkzeug.utils import secure_filename
import sqlite3
import json
import os
import uuid

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "temporary_secret_key_change_later")


DATABASE = "menu.db"
OLD_JSON_FILE = "menu_data.json"

UPLOAD_FOLDER = os.path.join("static", "uploads")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "bliss123")


# -----------------------------
# Helper functions
# -----------------------------


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def generate_id(text="item"):
    safe_text = text.lower().strip().replace(" ", "_")
    short_uuid = str(uuid.uuid4())[:8]
    return f"{safe_text}_{short_uuid}"


def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_db()

    conn.executescript("""
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
    """)

    conn.commit()
    conn.close()


def row_to_item(row):
    return {
        "id": row["id"],
        "name_en": row["name_en"],
        "name_mk": row["name_mk"],
        "description_en": row["description_en"],
        "description_mk": row["description_mk"],
        "price": row["price"],
        "image": row["image"],
        "featured": bool(row["featured"]),
    }


def insert_json_item(conn, item, category_id, subcategory_id=None):
    item_id = item.get("id") or generate_id(item.get("name_en", "item"))

    conn.execute(
        """
        INSERT OR REPLACE INTO items (
            id,
            category_id,
            subcategory_id,
            name_en,
            name_mk,
            description_en,
            description_mk,
            price,
            image,
            featured
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


def import_old_json_if_database_empty():
    if not os.path.exists(OLD_JSON_FILE):
        return

    conn = get_db()

    category_count = conn.execute(
        "SELECT COUNT(*) AS total FROM categories"
    ).fetchone()["total"]

    if category_count > 0:
        conn.close()
        return

    try:
        with open(OLD_JSON_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)

        for category in data.get("categories", []):
            category_id = category.get("id") or generate_id(
                category.get("name_en", "category")
            )

            conn.execute(
                """
                INSERT OR REPLACE INTO categories (
                    id,
                    name_en,
                    name_mk
                )
                VALUES (?, ?, ?)
                """,
                (
                    category_id,
                    category.get("name_en", ""),
                    category.get("name_mk", ""),
                ),
            )

            for item in category.get("items", []):
                insert_json_item(conn, item, category_id)

            for subcategory in category.get("subcategories", []):
                subcategory_id = subcategory.get("id") or generate_id(
                    subcategory.get("name_en", "subcategory")
                )

                conn.execute(
                    """
                    INSERT OR REPLACE INTO subcategories (
                        id,
                        category_id,
                        name_en,
                        name_mk
                    )
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
                    insert_json_item(conn, item, category_id, subcategory_id)

        conn.commit()
        print("Old menu_data.json was imported into menu.db.")

    except Exception as error:
        print("Could not import menu_data.json:", error)

    finally:
        conn.close()


def load_data():
    conn = get_db()

    categories = conn.execute("SELECT * FROM categories ORDER BY rowid").fetchall()

    data = {"categories": []}

    for category in categories:
        category_data = {
            "id": category["id"],
            "name_en": category["name_en"],
            "name_mk": category["name_mk"],
            "items": [],
            "subcategories": [],
        }

        category_items = conn.execute(
            """
            SELECT *
            FROM items
            WHERE category_id = ?
            AND subcategory_id IS NULL
            ORDER BY rowid
            """,
            (category["id"],),
        ).fetchall()

        category_data["items"] = [row_to_item(item) for item in category_items]

        subcategories = conn.execute(
            """
            SELECT *
            FROM subcategories
            WHERE category_id = ?
            ORDER BY rowid
            """,
            (category["id"],),
        ).fetchall()

        for subcategory in subcategories:
            subcategory_data = {
                "id": subcategory["id"],
                "name_en": subcategory["name_en"],
                "name_mk": subcategory["name_mk"],
                "items": [],
            }

            subcategory_items = conn.execute(
                """
                SELECT *
                FROM items
                WHERE subcategory_id = ?
                ORDER BY rowid
                """,
                (subcategory["id"],),
            ).fetchall()

            subcategory_data["items"] = [
                row_to_item(item) for item in subcategory_items
            ]

            category_data["subcategories"].append(subcategory_data)

        data["categories"].append(category_data)

    conn.close()
    return data


def api_login_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not session.get("admin_logged_in"):
            return redirect(url_for("login"))

        return func(*args, **kwargs)

    return wrapper


# -----------------------------
# Language / translation helpers
# -----------------------------


def get_language():
    lang = request.args.get("lang", "en")

    if lang not in ["en", "mk"]:
        lang = "en"

    return lang


def translate_item(item, lang):
    return {
        "id": item["id"],
        "name": item.get(f"name_{lang}", item.get("name_en", "")),
        "name_en": item.get("name_en", ""),
        "name_mk": item.get("name_mk", ""),
        "description": item.get(f"description_{lang}", item.get("description_en", "")),
        "description_en": item.get("description_en", ""),
        "description_mk": item.get("description_mk", ""),
        "price": item.get("price", ""),
        "image": item.get("image", ""),
        "featured": item.get("featured", False),
    }


def translate_subcategory(subcategory, lang):
    return {
        "id": subcategory["id"],
        "name": subcategory.get(f"name_{lang}", subcategory.get("name_en", "")),
        "name_en": subcategory.get("name_en", ""),
        "name_mk": subcategory.get("name_mk", ""),
        "items": [translate_item(item, lang) for item in subcategory.get("items", [])],
    }


def translate_category(category, lang):
    return {
        "id": category["id"],
        "name": category.get(f"name_{lang}", category.get("name_en", "")),
        "name_en": category.get("name_en", ""),
        "name_mk": category.get("name_mk", ""),
        "items": [translate_item(item, lang) for item in category.get("items", [])],
        "subcategories": [
            translate_subcategory(subcategory, lang)
            for subcategory in category.get("subcategories", [])
        ],
    }


def get_featured_items(data, lang):
    featured_items = []

    for category in data.get("categories", []):
        for item in category.get("items", []):
            if item.get("featured"):
                featured_items.append(translate_item(item, lang))

        for subcategory in category.get("subcategories", []):
            for item in subcategory.get("items", []):
                if item.get("featured"):
                    featured_items.append(translate_item(item, lang))

    return featured_items


# -----------------------------
# Public pages
# -----------------------------


@app.route("/")
def home():
    lang = get_language()
    data = load_data()

    translated_categories = [
        translate_category(category, lang) for category in data["categories"]
    ]

    featured_items = get_featured_items(data, lang)

    return render_template(
        "index.html",
        lang=lang,
        categories=translated_categories,
        featured_items=featured_items,
    )


# -----------------------------
# Admin login
# -----------------------------


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session["admin_logged_in"] = True
            return redirect(url_for("admin"))

        error = "Wrong username or password."

    return render_template("login.html", error=error)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


@app.route("/admin")
@api_login_required
def admin():
    data = load_data()
    return render_template("admin.html", data=data)


# -----------------------------
# Public API
# -----------------------------


@app.route("/api/menu")
def api_menu():
    lang = get_language()
    data = load_data()

    translated_categories = [
        translate_category(category, lang) for category in data["categories"]
    ]

    featured_items = get_featured_items(data, lang)

    return jsonify(
        {
            "language": lang,
            "categories": translated_categories,
            "featured_items": featured_items,
        }
    )


# -----------------------------
# Category API
# -----------------------------


@app.route("/api/categories", methods=["POST"])
@api_login_required
def add_category():
    body = request.get_json(silent=True) or request.form

    name_en = body.get("name_en")
    name_mk = body.get("name_mk")

    if not name_en or not name_mk:
        if request.is_json:
            return (
                jsonify({"error": "English name and Macedonian name are required."}),
                400,
            )

        return redirect(url_for("admin"))

    new_category = {
        "id": generate_id(name_en),
        "name_en": name_en,
        "name_mk": name_mk,
        "items": [],
        "subcategories": [],
    }

    conn = get_db()

    conn.execute(
        """
        INSERT INTO categories (
            id,
            name_en,
            name_mk
        )
        VALUES (?, ?, ?)
        """,
        (
            new_category["id"],
            name_en,
            name_mk,
        ),
    )

    conn.commit()
    conn.close()

    if request.is_json:
        return (
            jsonify(
                {
                    "message": "Category added.",
                    "category": new_category,
                }
            ),
            201,
        )

    return redirect(url_for("admin"))


@app.route("/api/categories/<category_id>", methods=["DELETE"])
@api_login_required
def delete_category(category_id):
    conn = get_db()

    cursor = conn.execute(
        "DELETE FROM categories WHERE id = ?",
        (category_id,),
    )

    conn.commit()
    deleted = cursor.rowcount
    conn.close()

    if deleted == 0:
        return jsonify({"error": "Category not found."}), 404

    return jsonify({"message": "Category deleted."})


# -----------------------------
# Subcategory API
# -----------------------------


@app.route("/api/subcategories", methods=["POST"])
@api_login_required
def add_subcategory():
    body = request.get_json(silent=True) or request.form

    category_id = body.get("category_id")
    name_en = body.get("name_en")
    name_mk = body.get("name_mk")

    if not category_id or not name_en or not name_mk:
        if request.is_json:
            return (
                jsonify(
                    {
                        "error": "Category ID, English name and Macedonian name are required."
                    }
                ),
                400,
            )

        return redirect(url_for("admin"))

    conn = get_db()

    category = conn.execute(
        "SELECT id FROM categories WHERE id = ?",
        (category_id,),
    ).fetchone()

    if not category:
        conn.close()

        if request.is_json:
            return jsonify({"error": "Category not found."}), 404

        return redirect(url_for("admin"))

    new_subcategory = {
        "id": generate_id(name_en),
        "name_en": name_en,
        "name_mk": name_mk,
        "items": [],
    }

    conn.execute(
        """
        INSERT INTO subcategories (
            id,
            category_id,
            name_en,
            name_mk
        )
        VALUES (?, ?, ?, ?)
        """,
        (
            new_subcategory["id"],
            category_id,
            name_en,
            name_mk,
        ),
    )

    conn.commit()
    conn.close()

    if request.is_json:
        return (
            jsonify(
                {
                    "message": "Subcategory added.",
                    "subcategory": new_subcategory,
                }
            ),
            201,
        )

    return redirect(url_for("admin"))


@app.route("/api/subcategories/<subcategory_id>", methods=["DELETE"])
@api_login_required
def delete_subcategory(subcategory_id):
    conn = get_db()

    cursor = conn.execute(
        "DELETE FROM subcategories WHERE id = ?",
        (subcategory_id,),
    )

    conn.commit()
    deleted = cursor.rowcount
    conn.close()

    if deleted == 0:
        return jsonify({"error": "Subcategory not found."}), 404

    return jsonify({"message": "Subcategory deleted."})


# -----------------------------
# Item API
# -----------------------------


@app.route("/api/items", methods=["POST"])
@api_login_required
def add_item():
    body = request.get_json(silent=True) or request.form

    target_id = body.get("target_id", "")

    category_id = body.get("category_id", "")
    subcategory_id = body.get("subcategory_id", "")

    if target_id.startswith("category|"):
        category_id = target_id.split("|", 1)[1]
        subcategory_id = ""

    if target_id.startswith("subcategory|"):
        subcategory_id = target_id.split("|", 1)[1]
        category_id = ""

    name_en = body.get("name_en")
    name_mk = body.get("name_mk")
    description_en = body.get("description_en", "")
    description_mk = body.get("description_mk", "")
    price = body.get("price", "")
    image = body.get("image", "")
    featured = body.get("featured", False)

    image_file = request.files.get("image_file")

    if image_file and image_file.filename != "":
        if allowed_file(image_file.filename):
            safe_filename = secure_filename(image_file.filename)
            unique_filename = f"{uuid.uuid4().hex}_{safe_filename}"

            image_path = os.path.join(app.config["UPLOAD_FOLDER"], unique_filename)
            image_file.save(image_path)

            image = f"uploads/{unique_filename}"
        else:
            return "Invalid image type. Use PNG, JPG, JPEG, WEBP, or GIF.", 400

    featured = featured in ["true", "True", "on", "1", True]

    if not name_en or not name_mk:
        if request.is_json:
            return (
                jsonify({"error": "English name and Macedonian name are required."}),
                400,
            )

        return redirect(url_for("admin"))

    new_item = {
        "id": generate_id(name_en),
        "name_en": name_en,
        "name_mk": name_mk,
        "description_en": description_en,
        "description_mk": description_mk,
        "price": price,
        "image": image,
        "featured": featured,
    }

    conn = get_db()

    if subcategory_id:
        subcategory = conn.execute(
            """
            SELECT id, category_id
            FROM subcategories
            WHERE id = ?
            """,
            (subcategory_id,),
        ).fetchone()

        if not subcategory:
            conn.close()

            if request.is_json:
                return jsonify({"error": "Subcategory not found."}), 404

            return redirect(url_for("admin"))

        conn.execute(
            """
            INSERT INTO items (
                id,
                category_id,
                subcategory_id,
                name_en,
                name_mk,
                description_en,
                description_mk,
                price,
                image,
                featured
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                new_item["id"],
                subcategory["category_id"],
                subcategory_id,
                name_en,
                name_mk,
                description_en,
                description_mk,
                price,
                image,
                int(featured),
            ),
        )

        conn.commit()
        conn.close()

        if request.is_json:
            return (
                jsonify(
                    {
                        "message": "Item added to subcategory.",
                        "item": new_item,
                    }
                ),
                201,
            )

        return redirect(url_for("admin"))

    if category_id:
        category = conn.execute(
            "SELECT id FROM categories WHERE id = ?",
            (category_id,),
        ).fetchone()

        if not category:
            conn.close()

            if request.is_json:
                return jsonify({"error": "Category not found."}), 404

            return redirect(url_for("admin"))

        conn.execute(
            """
            INSERT INTO items (
                id,
                category_id,
                subcategory_id,
                name_en,
                name_mk,
                description_en,
                description_mk,
                price,
                image,
                featured
            )
            VALUES (?, ?, NULL, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                new_item["id"],
                category_id,
                name_en,
                name_mk,
                description_en,
                description_mk,
                price,
                image,
                int(featured),
            ),
        )

        conn.commit()
        conn.close()

        if request.is_json:
            return (
                jsonify(
                    {
                        "message": "Item added to category.",
                        "item": new_item,
                    }
                ),
                201,
            )

        return redirect(url_for("admin"))

    conn.close()

    if request.is_json:
        return jsonify({"error": "Choose a category or subcategory."}), 400

    return redirect(url_for("admin"))


@app.route("/api/items/<item_id>", methods=["PUT"])
@api_login_required
def update_item(item_id):
    body = request.get_json(silent=True) or request.form

    conn = get_db()

    existing_item = conn.execute(
        "SELECT * FROM items WHERE id = ?",
        (item_id,),
    ).fetchone()

    if not existing_item:
        conn.close()
        return jsonify({"error": "Item not found."}), 404

    name_en = body.get("name_en", existing_item["name_en"])
    name_mk = body.get("name_mk", existing_item["name_mk"])
    description_en = body.get("description_en", existing_item["description_en"])
    description_mk = body.get("description_mk", existing_item["description_mk"])
    price = body.get("price", existing_item["price"])
    image = body.get("image", existing_item["image"])

    image_file = request.files.get("image_file")

    if image_file and image_file.filename != "":
        if allowed_file(image_file.filename):
            safe_filename = secure_filename(image_file.filename)
            unique_filename = f"{uuid.uuid4().hex}_{safe_filename}"

            image_path = os.path.join(app.config["UPLOAD_FOLDER"], unique_filename)
            image_file.save(image_path)

            image = f"uploads/{unique_filename}"
        else:
            conn.close()
            return "Invalid image type. Use PNG, JPG, JPEG, WEBP, or GIF.", 400

    if "featured" in body:
        featured = body.get("featured") in ["true", "True", "on", "1", True]
    else:
        featured = bool(existing_item["featured"])

    conn.execute(
        """
        UPDATE items
        SET name_en = ?,
            name_mk = ?,
            description_en = ?,
            description_mk = ?,
            price = ?,
            image = ?,
            featured = ?
        WHERE id = ?
        """,
        (
            name_en,
            name_mk,
            description_en,
            description_mk,
            price,
            image,
            int(featured),
            item_id,
        ),
    )

    conn.commit()

    updated_item = conn.execute(
        "SELECT * FROM items WHERE id = ?",
        (item_id,),
    ).fetchone()

    conn.close()

    return jsonify(
        {
            "message": "Item updated.",
            "item": row_to_item(updated_item),
        }
    )


@app.route("/api/items/<item_id>", methods=["DELETE"])
@api_login_required
def delete_item(item_id):
    conn = get_db()

    cursor = conn.execute(
        "DELETE FROM items WHERE id = ?",
        (item_id,),
    )

    conn.commit()
    deleted = cursor.rowcount
    conn.close()

    if deleted == 0:
        return jsonify({"error": "Item not found."}), 404

    return jsonify({"message": "Item deleted."})


# -----------------------------
# Start database
# -----------------------------

init_db()
import_old_json_if_database_empty()


# -----------------------------
# Run app
# -----------------------------

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
