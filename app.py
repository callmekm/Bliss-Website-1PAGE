from flask import Flask, render_template, redirect, request, url_for, session, jsonify
from functools import wraps
import json
import os
import uuid

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "temporary_secret_key_change_later")

DATA_FILE = "menu_data.json"

ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "bliss123")

# Helper functions


def load_data():
    if not os.path.exists(DATA_FILE):
        return {"categories": []}

    with open(DATA_FILE, "r", encoding="utf-8") as file:
        return json.load(file)


def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4, ensure_ascii=False)


def generate_id(text="item"):
    safe_text = text.lower().strip().replace(" ", "_")
    short_uuid = str(uuid.uuid4())[:8]
    return f"{safe_text}_{short_uuid}"


def translate_category(item, lang):
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


def api_login_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not session.get("admin_logged_in"):
            return redirect(url_for("login"))
        return func(*args, **kwargs)

    return wrapper


# Landing Page


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


def translate_category(category, lang):
    return {
        "id": category["id"],
        "name": category.get(f"name_{lang}", category.get("name_en", "")),
        "name_en": category.get("name_en", ""),
        "name_mk": category.get("name_mk", ""),
        "items": [translate_item(item, lang) for item in category.get("items", [])],
    }


@app.route("/")
def home():
    lang = get_language()
    data = load_data()

    translated_categories = [
        translate_category(category, lang) for category in data["categories"]
    ]

    featured_items = []
    for category in data["categories"]:
        for item in category.get("items", []):
            if item.get("featured"):
                featured_items.append(translate_item(item, lang))

    return render_template(
        "index.html",
        lang=lang,
        categories=translated_categories,
        featured_items=featured_items,
    )


# Admin Page


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


# Public API


@app.route("/api/menu")
def api_menu():
    lang = get_language()
    data = load_data()

    translated_categories = [
        translate_category(category, lang) for category in data["categories"]
    ]

    featured_items = []
    for category in data["categories"]:
        for item in category.get("items", []):
            if item.get("featured"):
                featured_items.append(translate_item(item, lang))

    return jsonify(
        {
            "language": lang,
            "categories": translated_categories,
            "featured_items": featured_items,
        }
    )


# Category API


@app.route("/api/categories", methods=["POST"])
@api_login_required
def add_category():
    data = load_data()

    name_en = request.form.get("name_en") or request.json.get("name_en")
    name_mk = request.form.get("name_mk") or request.json.get("name_mk")

    if not name_en or not name_mk:
        return (
            jsonify({"error": "English and Macedonian category names are required."}),
            400,
        )

    new_category = {
        "id": generate_id(name_en),
        "name_en": name_en,
        "name_mk": name_mk,
        "items": [],
    }

    data["categories"].append(new_category)
    save_data(data)

    return jsonify({"message": "Category added.", "category": new_category}), 201


@app.route("/api/categories/<category_id>", methods=["PUT"])
@api_login_required
def update_category(category_id):
    data = load_data()
    body = request.json or request.form

    for category in data["categories"]:
        if category["id"] == category_id:
            category["name_en"] = body.get("name_en", category["name_en"])
            category["name_mk"] = body.get("name_mk", category["name_mk"])
            save_data(data)
            return jsonify({"message": "Category updated.", "category": category})

    return jsonify({"error": "Category not found."}), 404


@app.route("/api/categories/<category_id>", methods=["DELETE"])
@api_login_required
def delete_category(category_id):
    data = load_data()

    original_count = len(data["categories"])
    data["categories"] = [
        category for category in data["categories"] if category["id"] != category_id
    ]

    if len(data["categories"]) == original_count:
        return jsonify({"error": "Category not found."}), 404

    save_data(data)
    return jsonify({"message": "Category deleted."})


# Item API


@app.route("/api/items", methods=["POST"])
@api_login_required
def add_item():
    data = load_data()
    body = request.json or request.form

    category_id = body.get("category_id")
    name_en = body.get("name_en")
    name_mk = body.get("name_mk")
    description_en = body.get("description_en", "")
    description_mk = body.get("description_mk", "")
    price = body.get("price", "")
    image = body.get("image", "")
    featured = body.get("featured", False)

    if featured in ["true", "True", "on", "1"]:
        featured = True
    else:
        featured = False

    if not category_id or not name_en or not name_mk:
        return (
            jsonify(
                {"error": "Category, English name and Macedonian name are required."}
            ),
            400,
        )

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

    for category in data["categories"]:
        if category["id"] == category_id:
            category["items"].append(new_item)
            save_data(data)
            return jsonify({"message": "Item added.", "item": new_item}), 201

    return jsonify({"error": "Category not found."}), 404


@app.route("/api/items/<item_id>", methods=["PUT"])
@api_login_required
def update_item(item_id):
    data = load_data()
    body = request.json or request.form

    for category in data["categories"]:
        for item in category.get("items", []):
            if item["id"] == item_id:
                item["name_en"] = body.get("name_en", item["name_en"])
                item["name_mk"] = body.get("name_mk", item["name_mk"])
                item["description_en"] = body.get(
                    "description_en", item["description_en"]
                )
                item["description_mk"] = body.get(
                    "description_mk", item["description_mk"]
                )
                item["price"] = body.get("price", item["price"])
                item["image"] = body.get("image", item["image"])

                if "featured" in body:
                    item["featured"] = body.get("featured") in [
                        "true",
                        "True",
                        "on",
                        "1",
                        True,
                    ]

                save_data(data)
                return jsonify({"message": "Item updated.", "item": item})

    return jsonify({"error": "Item not found."}), 404


@app.route("/api/items/<item_id>", methods=["DELETE"])
@api_login_required
def delete_item(item_id):
    data = load_data()

    for category in data["categories"]:
        original_count = len(category.get("items", []))
        category["items"] = [
            item for item in category.get("items", []) if item["id"] != item_id
        ]

        if len(category["items"]) != original_count:
            save_data(data)
            return jsonify({"message": "Item deleted."})

    return jsonify({"error": "Item not found."}), 404


# Run app

if __name__ == "__main__":
    app.run(debug=True)
