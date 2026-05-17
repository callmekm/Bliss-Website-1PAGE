from flask import Flask, render_template, redirect, request, url_for, session, jsonify
from functools import wraps
from werkzeug.utils import secure_filename
import sqlite3
import json
import os
import uuid

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "temporary_secret_key_change_later")

# Always use paths next to this app file — relative "menu.db" breaks if the server
# cwd is not the project directory (empty DB → no such table: categories).
DATABASE = os.path.join(app.root_path, "menu.db")
OLD_JSON_FILE = os.path.join(app.root_path, "menu_data.json")

UPLOAD_FOLDER = os.path.join(app.root_path, "static", "uploads")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "bliss123")


@app.before_request
def persist_language_from_query():
    """Keep ?lang=en|mk in session so login, admin, and redirects stay consistent."""
    lang = request.args.get("lang")
    if lang in ("en", "mk"):
        session["lang"] = lang


# -----------------------------
# Helper functions
# -----------------------------


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def delete_uploaded_image(image_path):
    if not image_path:
        return

    image_path = image_path.replace("\\", "/").strip()

    # Only delete files from static/uploads
    if not image_path.startswith("uploads/"):
        return

    filename = os.path.basename(image_path)

    uploads_dir = os.path.abspath(
        os.path.join(app.root_path, app.config["UPLOAD_FOLDER"])
    )

    full_path = os.path.abspath(os.path.join(uploads_dir, filename))

    # Saftey check to prevent deleting files outside of uploads
    if not full_path.startswith(uploads_dir):
        return

    if os.path.exists(full_path):
        os.remove(full_path)


def generate_id(text="item"):
    safe_text = text.lower().strip().replace(" ", "_")
    short_uuid = str(uuid.uuid4())[:8]
    return f"{safe_text}_{short_uuid}"


def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# Client menu category order (EN / MK names unchanged)
CATEGORY_DISPLAY_ORDER = [
    "non_alcoholic_drinks",
    "alcoholic_drinks",
    "cocktails",
    "food",
    "desserts",
]


def ensure_category_sort_column(conn):
    columns = {
        row[1] for row in conn.execute("PRAGMA table_info(categories)").fetchall()
    }
    if "sort_order" not in columns:
        conn.execute(
            "ALTER TABLE categories ADD COLUMN sort_order INTEGER NOT NULL DEFAULT 0"
        )
        conn.commit()


def apply_category_sort_order(conn):
    for order, category_id in enumerate(CATEGORY_DISPLAY_ORDER):
        conn.execute(
            "UPDATE categories SET sort_order = ? WHERE id = ?",
            (order, category_id),
        )
    conn.commit()


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
        CREATE TABLE IF NOT EXISTS featured_items (
    id TEXT PRIMARY KEY,
    label_en TEXT DEFAULT '',
    label_mk TEXT DEFAULT '',
    title_en TEXT NOT NULL,
    title_mk TEXT NOT NULL,
    description_en TEXT DEFAULT '',
    description_mk TEXT DEFAULT '',
    price TEXT DEFAULT '',
    image TEXT DEFAULT '',
    active INTEGER DEFAULT 1,
    sort_order INTEGER DEFAULT 0
);
    """)

    conn.commit()
    ensure_category_sort_column(conn)
    apply_category_sort_order(conn)
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

        for sort_order, category in enumerate(data.get("categories", [])):
            category_id = category.get("id") or generate_id(
                category.get("name_en", "category")
            )

            conn.execute(
                """
                INSERT OR REPLACE INTO categories (
                    id,
                    name_en,
                    name_mk,
                    sort_order
                )
                VALUES (?, ?, ?, ?)
                """,
                (
                    category_id,
                    category.get("name_en", ""),
                    category.get("name_mk", ""),
                    sort_order,
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
    init_db()

    conn = get_db()

    categories = conn.execute(
        "SELECT * FROM categories ORDER BY sort_order, name_en COLLATE NOCASE"
    ).fetchall()

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
            ORDER BY name_en COLLATE NOCASE
            """,
            (category["id"],),
        ).fetchall()

        category_data["items"] = [row_to_item(item) for item in category_items]

        subcategories = conn.execute(
            """
            SELECT *
            FROM subcategories
            WHERE category_id = ?
            ORDER BY name_en COLLATE NOCASE
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
                ORDER BY name_en COLLATE NOCASE
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
            return redirect(url_for("login", lang=get_language()))

        return func(*args, **kwargs)

    return wrapper

def row_to_featured_item(row, lang="en"):
    return {
        "id": row["id"],

        "label": row[f"label_{lang}"] or row["label_en"],
        "label_en": row["label_en"],
        "label_mk": row["label_mk"],

        "title": row[f"title_{lang}"] or row["title_en"],
        "title_en": row["title_en"],
        "title_mk": row["title_mk"],

        "description": row[f"description_{lang}"] or row["description_en"],
        "description_en": row["description_en"],
        "description_mk": row["description_mk"],

        "price": row["price"],
        "image": row["image"],
        "active": bool(row["active"]),
        "sort_order": row["sort_order"],
    }


def load_featured_items(lang="en"):
    conn = get_db()

    rows = conn.execute(
        """
        SELECT *
        FROM featured_items
        WHERE active = 1
        ORDER BY sort_order, rowid
        """
    ).fetchall()

    conn.close()

    return [row_to_featured_item(row, lang) for row in rows]


# -----------------------------
# Language / translation helpers
# -----------------------------


def get_language():
    lang = session.get("lang", "en")
    if lang not in ("en", "mk"):
        return "en"
    return lang


def redirect_admin():
    return redirect(url_for("admin", lang=get_language()))


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

    featured_items = load_featured_items(lang)

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
    lang = get_language()
    login_failed = False

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session["admin_logged_in"] = True
            return redirect_admin()

        login_failed = True

    return render_template("login.html", lang=lang, login_failed=login_failed)


@app.route("/logout")
def logout():
    lang = session.get("lang", "en")
    if lang not in ("en", "mk"):
        lang = "en"
    session.clear()
    session["lang"] = lang
    return redirect(url_for("home", lang=lang))


@app.route("/admin")
@api_login_required
def admin():
    lang = get_language()
    data = load_data()
    featured_items = load_featured_items(lang)

    return render_template(
        "admin.html",
        data=data,
        lang=lang,
        featured_items=featured_items,
    )


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

    featured_items = load_featured_items(lang)

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

        return redirect_admin()

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

    return redirect_admin()


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

        return redirect_admin()

    conn = get_db()

    category = conn.execute(
        "SELECT id FROM categories WHERE id = ?",
        (category_id,),
    ).fetchone()

    if not category:
        conn.close()

        if request.is_json:
            return jsonify({"error": "Category not found."}), 404

        return redirect_admin()

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

    return redirect_admin()


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
# Featured Items API
# -----------------------------
@app.route("/api/featured-items", methods=["POST"])
@api_login_required
def add_featured_item():
    body = request.form

    label_en = body.get("label_en", "")
    label_mk = body.get("label_mk", "")
    title_en = body.get("title_en", "")
    title_mk = body.get("title_mk", "")
    description_en = body.get("description_en", "")
    description_mk = body.get("description_mk", "")
    price = body.get("price", "")
    sort_order = body.get("sort_order", 0)
    active = body.get("active", False)

    image = ""
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

    active = active in ["true", "True", "on", "1", True]

    if not title_en or not title_mk:
        return redirect(url_for("admin"))

    conn = get_db()

    conn.execute(
        """
        INSERT INTO featured_items (
            id,
            label_en,
            label_mk,
            title_en,
            title_mk,
            description_en,
            description_mk,
            price,
            image,
            active,
            sort_order
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            generate_id(title_en),
            label_en,
            label_mk,
            title_en,
            title_mk,
            description_en,
            description_mk,
            price,
            image,
            int(active),
            int(sort_order or 0),
        ),
    )

    conn.commit()
    conn.close()

    return redirect(url_for("admin"))


@app.route("/api/featured-items/<featured_id>", methods=["DELETE"])
@api_login_required
def delete_featured_item(featured_id):
    conn = get_db()

    cursor = conn.execute(
        "DELETE FROM featured_items WHERE id = ?",
        (featured_id,),
    )

    conn.commit()
    deleted = cursor.rowcount
    conn.close()

    if deleted == 0:
        return jsonify({"error": "Featured item not found."}), 404

    return jsonify({"message": "Featured item deleted."})


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

        return redirect_admin()

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

            return redirect_admin()

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

        return redirect_admin()

    if category_id:
        category = conn.execute(
            "SELECT id FROM categories WHERE id = ?",
            (category_id,),
        ).fetchone()

        if not category:
            conn.close()

            if request.is_json:
                return jsonify({"error": "Category not found."}), 404

            return redirect_admin()

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

        return redirect_admin()

    conn.close()

    if request.is_json:
        return jsonify({"error": "Choose a category or subcategory."}), 400

    return redirect_admin()


@app.route("/api/items/<item_id>", methods=["GET"])
@api_login_required
def get_item(item_id):
    conn = get_db()

    item = conn.execute(
        "SELECT * FROM items WHERE id = ?",
        (item_id,),
    ).fetchone()

    conn.close()

    if not item:
        return jsonify({"error": "Item not found."}), 404

    return jsonify(row_to_item(item))

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
    old_image = existing_item["image"]
    image = body.get("image", old_image)
    delete_old_image_after_update = False

    image_file = request.files.get("image_file")

    if image_file and image_file.filename != "":
        if allowed_file(image_file.filename):
            safe_filename = secure_filename(image_file.filename)
            unique_filename = f"{uuid.uuid4().hex}_{safe_filename}"

            image_path = os.path.join(app.config["UPLOAD_FOLDER"], unique_filename)
            image_file.save(image_path)

            image = f"uploads/{unique_filename}"
            delete_old_image_after_update = True
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

    if delete_old_image_after_update and old_image and old_image != image:
        delete_uploaded_image(old_image)

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


@app.route("/api/items/<item_id>/image", methods=["DELETE"])
@api_login_required
def delete_item_image(item_id):
    conn = get_db()

    existing_item = conn.execute(
        "SELECT image FROM items WHERE id = ?",
        (item_id,),
    ).fetchone()

    if not existing_item:
        conn.close()
        return jsonify({"error": "Item not found."}), 404

    old_image = existing_item["image"]

    conn.execute(
        "UPDATE items SET image = '' WHERE id = ?",
        (item_id,),
    )

    conn.commit()
    conn.close()

    delete_uploaded_image(old_image)
    return jsonify({"message": "Item image deleted."})


@app.route("/api/items/<item_id>", methods=["DELETE"])
@api_login_required
def delete_item(item_id):
    conn = get_db()

    existing_item = conn.execute(
        "SELECT image FROM items WHERE id = ?",
        (item_id,),
    ).fetchone()

    if not existing_item:
        conn.close()
        return jsonify({"error": "Item not found."}), 404

    old_image = existing_item["image"]

    cursor = conn.execute(
        "DELETE FROM items WHERE id = ?",
        (item_id,),
    )

    conn.commit()
    deleted = cursor.rowcount
    conn.close()

    if deleted == 0:
        return jsonify({"error": "Item not found."}), 404

    delete_uploaded_image(old_image)

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
