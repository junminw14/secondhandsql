from __future__ import annotations

import os
import re
import sqlite3
import sys
import threading
import webbrowser
from datetime import date
from functools import wraps
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from dotenv import load_dotenv

from flask import Flask, flash, g, redirect, render_template, request, session, url_for

try:
    import psycopg
    from psycopg.rows import dict_row

    PSYCOPG_AVAILABLE = True
except ImportError:
    psycopg = None
    dict_row = None
    PSYCOPG_AVAILABLE = False


load_dotenv(".env.local")


if getattr(sys, "frozen", False):
    RESOURCE_DIR = Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
    RUNTIME_DIR = Path(sys.executable).resolve().parent
else:
    RESOURCE_DIR = Path(__file__).resolve().parent
    RUNTIME_DIR = RESOURCE_DIR

DATABASE_PATH = RUNTIME_DIR / "secondhandsql.db"
SCHEMA_PATH = RESOURCE_DIR / "schema.sql"
INIT_DATA_PATH = RESOURCE_DIR / "init_data.sql"

RAW_POSTGRES_DSN = (
    os.environ.get("POSTGRES_URL")
    or os.environ.get("POSTGRES_PRISMA_URL")
    or os.environ.get("DATABASE_URL")
    or ""
).strip()

SEED_USERS = [
    ("u001", "ZhangSan", "13800000001"),
    ("u002", "LiSi", "13800000002"),
    ("u003", "WangWu", "13800000003"),
    ("u004", "ZhaoLiu", "13800000004"),
]
SEED_ITEMS = [
    ("i001", "CalculusBook", "Book", 20, 0, "u001"),
    ("i002", "DeskLamp", "DailyGoods", 35, 1, "u002"),
    ("i003", "Microcontroller", "Electronics", 80, 0, "u001"),
    ("i004", "Chair", "Furniture", 50, 1, "u003"),
    ("i005", "WaterBottle", "DailyGoods", 15, 0, "u004"),
]
SEED_ORDERS = [
    ("o001", "i002", "u001", "2024-05-01"),
    ("o002", "i004", "u002", "2024-05-03"),
]


app = Flask(
    __name__,
    template_folder=str(RESOURCE_DIR / "templates"),
    static_folder=str(RESOURCE_DIR / "static"),
)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "secondhandsql-demo-secret")
app.config["TEMPLATES_AUTO_RELOAD"] = True

ADMIN_USERNAME = "root"
ADMIN_PASSWORD = "123456"


def is_admin() -> bool:
    return session.get("is_admin") is True


def admin_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if not is_admin():
            flash("Only root can modify data. Other users can only query.", "error")
            return redirect(request.referrer or url_for("index"))
        return view(*args, **kwargs)

    return wrapped_view


@app.context_processor
def inject_auth_state() -> dict[str, object]:
    return {"is_admin": is_admin(), "admin_username": ADMIN_USERNAME}


def sanitize_postgres_dsn(dsn: str) -> str:
    if not dsn:
        return ""

    parsed = urlsplit(dsn)
    allowed_query_keys = {
        "application_name",
        "channel_binding",
        "connect_timeout",
        "gssencmode",
        "keepalives",
        "keepalives_count",
        "keepalives_idle",
        "keepalives_interval",
        "options",
        "sslcert",
        "sslcompression",
        "sslcrl",
        "sslkey",
        "sslmode",
        "target_session_attrs",
    }
    query = urlencode(
        [
            (key, value)
            for key, value in parse_qsl(parsed.query, keep_blank_values=True)
            if key in allowed_query_keys
        ],
        doseq=True,
    )
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, query, parsed.fragment))


POSTGRES_DSN = sanitize_postgres_dsn(RAW_POSTGRES_DSN)


def is_postgres() -> bool:
    return bool(POSTGRES_DSN and PSYCOPG_AVAILABLE)


def get_db():
    if is_postgres():
        if "db" not in g:
            g.db = psycopg.connect(POSTGRES_DSN, row_factory=dict_row, prepare_threshold=None)
        return g.db

    if "db" not in g:
        connection = sqlite3.connect(DATABASE_PATH)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        g.db = connection
    return g.db


@app.teardown_appcontext
def close_db(_exception: BaseException | None) -> None:
    connection = g.pop("db", None)
    if connection is not None:
        connection.close()


def prepare_sql(query: str) -> str:
    if not is_postgres():
        return query

    query = re.sub(r'\b(FROM|JOIN)\s+user\b', r'\1 "user"', query, flags=re.IGNORECASE)
    query = re.sub(r'\b(INTO|UPDATE|TABLE)\s+user\b', r'\1 "user"', query, flags=re.IGNORECASE)
    return query.replace("?", "%s")


def execute_sql(query: str, params: tuple = ()):
    return get_db().execute(prepare_sql(query), params)


def fetch_all(query: str, params: tuple = ()) -> list:
    return execute_sql(query, params).fetchall()


def fetch_one(query: str, params: tuple = ()):
    return execute_sql(query, params).fetchone()


def commit_db() -> None:
    get_db().commit()


def rollback_db() -> None:
    get_db().rollback()


def execute_write(query: str, params: tuple = (), *, commit: bool = True) -> int:
    cursor = execute_sql(query, params)
    if commit:
        commit_db()
    return cursor.rowcount


def execute_sql_file(connection: sqlite3.Connection, path: Path) -> None:
    connection.executescript(path.read_text(encoding="utf-8"))


def init_database(force: bool = False) -> None:
    if force and DATABASE_PATH.exists():
        DATABASE_PATH.unlink()

    connection = sqlite3.connect(DATABASE_PATH)
    try:
        connection.execute("PRAGMA foreign_keys = ON")
        execute_sql_file(connection, SCHEMA_PATH)
        execute_sql_file(connection, INIT_DATA_PATH)
        connection.commit()
    finally:
        connection.close()


def ensure_database() -> None:
    if not is_postgres() and not DATABASE_PATH.exists():
        init_database()


def get_dashboard_stats() -> dict[str, str]:
    total_items = fetch_one("SELECT COUNT(*) AS count FROM item")["count"]
    unsold_items = fetch_one("SELECT COUNT(*) AS count FROM item WHERE status = 0")["count"]
    total_orders = fetch_one("SELECT COUNT(*) AS count FROM orders")["count"]
    total_users = fetch_one('SELECT COUNT(*) AS count FROM "user"')["count"]
    average_price = fetch_one("SELECT ROUND(AVG(price), 2) AS value FROM item")["value"]
    return {
        "商品总数": str(total_items),
        "未售商品": str(unsold_items),
        "订单总数": str(total_orders),
        "用户总数": str(total_users),
        "平均价格": f"{average_price or 0:.2f}",
    }


def get_items_with_seller() -> list:
    return fetch_all(
        """
        SELECT
            i.item_id,
            i.item_name,
            i.category,
            i.price,
            i.status,
            i.seller_id,
            u.user_name AS seller_name
        FROM item AS i
        JOIN "user" AS u ON u.user_id = i.seller_id
        ORDER BY i.item_id
        """
    )


def get_order_details() -> list:
    return fetch_all(
        """
        SELECT
            o.order_id,
            o.item_id,
            i.item_name,
            o.buyer_id,
            u.user_name AS buyer_name,
            o.order_date
        FROM orders AS o
        JOIN item AS i ON i.item_id = o.item_id
        JOIN "user" AS u ON u.user_id = o.buyer_id
        ORDER BY o.order_date, o.order_id
        """
    )


def get_query_definitions() -> list[dict[str, object]]:
    return [
        {
            "id": "basic1",
            "title": "Basic query 1: all unsold items",
            "sql": """SELECT item_id, item_name, category, price, seller_id
FROM item
WHERE status = 0
ORDER BY item_id;""",
            "columns": ["item_id", "item_name", "category", "price", "seller_id"],
        },
        {
            "id": "basic2",
            "title": "Basic query 2: items priced over 30",
            "sql": """SELECT item_id, item_name, price
FROM item
WHERE price > 30
ORDER BY price DESC, item_id;""",
            "columns": ["item_id", "item_name", "price"],
        },
        {
            "id": "basic3",
            "title": "Basic query 3: DailyGoods items",
            "sql": """SELECT item_id, item_name, category, price
FROM item
WHERE category = 'DailyGoods'
ORDER BY item_id;""",
            "columns": ["item_id", "item_name", "category", "price"],
        },
        {
            "id": "basic4",
            "title": "Basic query 4: all items sold by u001",
            "sql": """SELECT item_id, item_name, category, price, status
FROM item
WHERE seller_id = 'u001'
ORDER BY item_id;""",
            "columns": ["item_id", "item_name", "category", "price", "status"],
        },
        {
            "id": "join1",
            "title": "Join query 1: sold items and buyer names",
            "sql": """SELECT
    i.item_id,
    i.item_name,
    o.buyer_id,
    u.user_name AS buyer_name
FROM item AS i
JOIN orders AS o ON o.item_id = i.item_id
JOIN "user" AS u ON u.user_id = o.buyer_id
WHERE i.status = 1
ORDER BY i.item_id;""",
            "columns": ["item_id", "item_name", "buyer_id", "buyer_name"],
        },
        {
            "id": "join2",
            "title": "Join query 2: order item, buyer, and date",
            "sql": """SELECT
    o.order_id,
    i.item_name,
    u.user_name AS buyer_name,
    o.order_date
FROM orders AS o
JOIN item AS i ON i.item_id = o.item_id
JOIN "user" AS u ON u.user_id = o.buyer_id
ORDER BY o.order_date, o.order_id;""",
            "columns": ["order_id", "item_name", "buyer_name", "order_date"],
        },
        {
            "id": "join3",
            "title": "Join query 3: whether u001 items were purchased",
            "sql": """SELECT
    i.item_id,
    i.item_name,
    CASE
        WHEN o.order_id IS NULL THEN 'No'
        ELSE 'Yes'
    END AS is_purchased,
    COALESCE(o.buyer_id, '-') AS buyer_id
FROM item AS i
LEFT JOIN orders AS o ON o.item_id = i.item_id
WHERE i.seller_id = 'u001'
ORDER BY i.item_id;""",
            "columns": ["item_id", "item_name", "is_purchased", "buyer_id"],
        },
        {
            "id": "agg1",
            "title": "Aggregate 1: item count",
            "sql": """SELECT COUNT(*) AS total_items FROM item;""",
            "columns": ["total_items"],
        },
        {
            "id": "agg2",
            "title": "Aggregate 2: item count by category",
            "sql": """SELECT category, COUNT(*) AS item_count
FROM item
GROUP BY category
ORDER BY category;""",
            "columns": ["category", "item_count"],
        },
        {
            "id": "agg3",
            "title": "Aggregate 3: average item price",
            "sql": """SELECT ROUND(AVG(price), 2) AS average_price FROM item;""",
            "columns": ["average_price"],
        },
        {
            "id": "agg4",
            "title": "Aggregate 4: user with most listed items",
            "sql": """SELECT
    u.user_id,
    u.user_name,
    COUNT(i.item_id) AS item_count
FROM "user" AS u
LEFT JOIN item AS i ON i.seller_id = u.user_id
GROUP BY u.user_id, u.user_name
ORDER BY item_count DESC, u.user_id
LIMIT 1;""",
            "columns": ["user_id", "user_name", "item_count"],
        },
        {
            "id": "view1",
            "title": "View 1: sold items view",
            "sql": """SELECT item_id, item_name, buyer_id
FROM sold_items_view
ORDER BY item_id;""",
            "columns": ["item_id", "item_name", "buyer_id"],
        },
        {
            "id": "view2",
            "title": "View 2: unsold items view",
            "sql": """SELECT item_id, item_name, category, price, seller_id
FROM unsold_items_view
ORDER BY item_id;""",
            "columns": ["item_id", "item_name", "category", "price", "seller_id"],
        },
    ]


def execute_safe_query(sql: str) -> dict[str, object]:
    stripped_sql = sql.strip()
    query_without_trailing_semicolon = stripped_sql.rstrip(";").strip()
    upper_sql = query_without_trailing_semicolon.upper()

    if ";" in query_without_trailing_semicolon:
        raise ValueError("Only one SELECT statement is allowed.")

    forbidden_keywords = [
        "INSERT",
        "UPDATE",
        "DELETE",
        "DROP",
        "ALTER",
        "CREATE",
        "TRUNCATE",
        "REPLACE",
        "ATTACH",
        "DETACH",
        "PRAGMA",
        "LOAD_EXTENSION",
    ]
    for keyword in forbidden_keywords:
        if re.search(rf"\b{keyword}\b", upper_sql):
            raise ValueError(f"Statements containing {keyword} are not allowed; use SELECT only.")

    if not upper_sql.startswith("SELECT"):
        raise ValueError("Only SELECT statements are allowed.")

    try:
        cursor = execute_sql(query_without_trailing_semicolon)
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description] if cursor.description else []
        return {"columns": columns, "rows": rows}
    except (sqlite3.Error, Exception) as exc:
        rollback_db()
        raise ValueError(f"SQL execution failed: {exc}") from exc


def generate_order_id() -> str:
    rows = fetch_all("SELECT order_id FROM orders")
    max_number = 0
    for row in rows:
        digits = "".join(ch for ch in row["order_id"] if ch.isdigit())
        if digits:
            max_number = max(max_number, int(digits))
    return f"o{max_number + 1:03d}"


def purchase_item(item_id: str, buyer_id: str, order_id: str, order_date: str) -> None:
    db = get_db()
    try:
        if not is_postgres():
            db.execute("BEGIN IMMEDIATE")

        item = fetch_one("SELECT item_id, status FROM item WHERE item_id = ?", (item_id,))
        if item is None:
            raise ValueError("Item does not exist.")
        if item["status"] == 1:
            raise ValueError("Item is already sold.")

        updated = execute_write(
            "UPDATE item SET status = 1 WHERE item_id = ? AND status = 0",
            (item_id,),
            commit=False,
        )
        if updated != 1:
            raise ValueError("Item status update failed.")

        execute_write(
            """
            INSERT INTO orders (order_id, item_id, buyer_id, order_date)
            VALUES (?, ?, ?, ?)
            """,
            (order_id, item_id, buyer_id, order_date),
            commit=False,
        )
        commit_db()
    except Exception:
        rollback_db()
        raise


def reset_postgres_data() -> None:
    try:
        execute_write("DELETE FROM orders", commit=False)
        execute_write("DELETE FROM item", commit=False)
        execute_write('DELETE FROM "user"', commit=False)
        for user in SEED_USERS:
            execute_write(
                'INSERT INTO "user" (user_id, user_name, phone) VALUES (?, ?, ?)',
                user,
                commit=False,
            )
        for item in SEED_ITEMS:
            execute_write(
                """
                INSERT INTO item (item_id, item_name, category, price, status, seller_id)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                item,
                commit=False,
            )
        for order in SEED_ORDERS:
            execute_write(
                """
                INSERT INTO orders (order_id, item_id, buyer_id, order_date)
                VALUES (?, ?, ?, ?)
                """,
                order,
                commit=False,
            )
        commit_db()
    except Exception:
        rollback_db()
        raise


def open_browser_later(url: str) -> None:
    threading.Timer(1.0, lambda: webbrowser.open(url)).start()


@app.before_request
def ensure_database_before_request() -> None:
    ensure_database()


def reset_query_results() -> None:
    global query_results, custom_result, custom_error
    query_results = {}
    custom_result = None
    custom_error = None


@app.route("/")
def index():
    reset_query_results()
    return render_template(
        "index.html",
        stats=get_dashboard_stats(),
    )


@app.post("/login")
def login():
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
        session["is_admin"] = True
        flash("Logged in as root. Write operations are enabled.", "success")
    else:
        session.pop("is_admin", None)
        flash("Login failed: username or password is incorrect.", "error")
    return redirect(request.referrer or url_for("index"))


@app.post("/logout")
def logout():
    session.pop("is_admin", None)
    flash("Logged out. The site is now read-only.", "success")
    return redirect(request.referrer or url_for("index"))


@app.route("/users")
def users():
    reset_query_results()
    return render_template(
        "users.html",
        users=fetch_all('SELECT user_id, user_name, phone FROM "user" ORDER BY user_id'),
    )


@app.post("/users/add")
@admin_required
def add_user():
    user_id = request.form["user_id"].strip()
    user_name = request.form["user_name"].strip()
    phone = request.form["phone"].strip()

    try:
        if not user_id:
            raise ValueError("User ID cannot be empty.")
        if not user_id.startswith("u") or not user_id[1:].isdigit():
            raise ValueError("User ID must look like u005.")
        if not user_name:
            raise ValueError("User name cannot be empty.")
        validate_phone(phone)

        execute_write(
            'INSERT INTO "user" (user_id, user_name, phone) VALUES (?, ?, ?)',
            (user_id, user_name, phone),
        )
        flash(f"User {user_id} ({user_name}) was added.", "success")
    except Exception as exc:
        rollback_db()
        flash(f"Add failed: {exc}", "error")
    return redirect(url_for("users"))


@app.post("/users/update-phone")
@admin_required
def update_user_phone():
    user_id = request.form["user_id"].strip()
    phone = request.form["phone"].strip()

    try:
        if not user_id:
            raise ValueError("User ID cannot be empty.")
        validate_phone(phone)

        updated = execute_write(
            'UPDATE "user" SET phone = ? WHERE user_id = ?',
            (phone, user_id),
        )
        if updated == 0:
            flash("Update failed: user does not exist.", "error")
        else:
            flash(f"User {user_id} phone was updated.", "success")
    except Exception as exc:
        rollback_db()
        flash(f"Update failed: {exc}", "error")
    return redirect(url_for("users"))


@app.post("/users/delete")
@admin_required
def delete_user():
    user_id = request.form["user_id"].strip()

    try:
        if not user_id:
            raise ValueError("User ID cannot be empty.")

        item_count = fetch_one(
            "SELECT COUNT(*) AS count FROM item WHERE seller_id = ?",
            (user_id,),
        )["count"]
        order_count = fetch_one(
            "SELECT COUNT(*) AS count FROM orders WHERE buyer_id = ?",
            (user_id,),
        )["count"]
        if item_count > 0:
            raise ValueError(f"User has {item_count} listed item(s).")
        if order_count > 0:
            raise ValueError(f"User has {order_count} order(s).")

        deleted = execute_write('DELETE FROM "user" WHERE user_id = ?', (user_id,))
        if deleted == 0:
            flash("Delete failed: user does not exist.", "error")
        else:
            flash(f"User {user_id} was deleted.", "success")
    except Exception as exc:
        rollback_db()
        flash(f"Delete failed: {exc}", "error")
    return redirect(url_for("users"))


@app.route("/items")
def items():
    reset_query_results()
    users_list = fetch_all('SELECT user_id, user_name FROM "user" ORDER BY user_id')
    items_list = get_items_with_seller()
    unsold_items = [row for row in items_list if row["status"] == 0]
    return render_template(
        "items.html",
        items=items_list,
        users=users_list,
        unsold_items=unsold_items,
        suggested_order_id=generate_order_id(),
        today=date.today().isoformat(),
    )


def validate_item_id(item_id: str) -> None:
    if not item_id:
        raise ValueError("Item ID cannot be empty.")
    if not item_id.startswith("i") or not item_id[1:].isdigit():
        raise ValueError("Item ID must look like i001.")


def validate_order_id(order_id: str) -> None:
    if not order_id:
        raise ValueError("Order ID cannot be empty.")
    if not order_id.startswith("o") or not order_id[1:].isdigit():
        raise ValueError("Order ID must look like o001.")


def validate_price(price_str: str) -> float:
    try:
        price = float(price_str)
    except ValueError as exc:
        raise ValueError("Price must be a valid number.") from exc
    if price < 0:
        raise ValueError("Price cannot be negative.")
    if price > 999999.99:
        raise ValueError("Price is too large.")
    return price


def validate_phone(phone: str) -> None:
    if not phone:
        raise ValueError("Phone number cannot be empty.")
    if not phone.isdigit():
        raise ValueError("Phone number must contain digits only.")
    if len(phone) != 11:
        raise ValueError("Phone number must be 11 digits.")


@app.post("/items/add")
@admin_required
def add_item():
    item_id = request.form["item_id"].strip()
    item_name = request.form["item_name"].strip()
    category = request.form["category"].strip()
    seller_id = request.form["seller_id"].strip()
    price_str = request.form["price"].strip()

    try:
        validate_item_id(item_id)
        if not item_name:
            raise ValueError("Item name cannot be empty.")
        if not category:
            raise ValueError("Category cannot be empty.")
        price = validate_price(price_str)

        user = fetch_one('SELECT user_id FROM "user" WHERE user_id = ?', (seller_id,))
        if user is None:
            raise ValueError(f"Seller {seller_id} does not exist.")

        execute_write(
            """
            INSERT INTO item (item_id, item_name, category, price, status, seller_id)
            VALUES (?, ?, ?, ?, 0, ?)
            """,
            (item_id, item_name, category, price, seller_id),
        )
        flash(f"Item {item_id} was added.", "success")
    except Exception as exc:
        rollback_db()
        flash(f"Add failed: {exc}", "error")
    return redirect(url_for("items"))


@app.post("/items/update-price")
@admin_required
def update_price():
    item_id = request.form["item_id"].strip()
    price_str = request.form["price"].strip()

    try:
        validate_item_id(item_id)
        price = validate_price(price_str)

        updated = execute_write(
            "UPDATE item SET price = ? WHERE item_id = ?",
            (price, item_id),
        )
        if updated == 0:
            flash("Price update failed: item does not exist.", "error")
        else:
            flash(f"Item {item_id} price was updated.", "success")
    except Exception as exc:
        rollback_db()
        flash(f"Price update failed: {exc}", "error")
    return redirect(url_for("items"))


@app.post("/items/delete")
@admin_required
def delete_item():
    item_id = request.form["item_id"].strip()
    try:
        validate_item_id(item_id)
        item = fetch_one("SELECT status FROM item WHERE item_id = ?", (item_id,))
        if item is None:
            raise ValueError("Item does not exist.")
        if item["status"] == 1:
            raise ValueError("Sold items cannot be deleted.")

        execute_write("DELETE FROM item WHERE item_id = ?", (item_id,))
        flash(f"Item {item_id} was deleted.", "success")
    except Exception as exc:
        rollback_db()
        flash(f"Delete failed: {exc}", "error")
    return redirect(url_for("items"))


@app.post("/items/purchase")
@admin_required
def buy_item():
    item_id = request.form["item_id"].strip()
    buyer_id = request.form["buyer_id"].strip()
    order_id = request.form["order_id"].strip() or generate_order_id()
    order_date = request.form["order_date"].strip() or date.today().isoformat()

    try:
        validate_item_id(item_id)
        validate_order_id(order_id)

        user = fetch_one('SELECT user_id FROM "user" WHERE user_id = ?', (buyer_id,))
        if user is None:
            raise ValueError(f"Buyer {buyer_id} does not exist.")

        purchase_item(item_id, buyer_id, order_id, order_date)
        flash(
            f"Purchase succeeded: order {order_id} was created and item {item_id} was marked sold.",
            "success",
        )
    except Exception as exc:
        rollback_db()
        flash(f"Purchase failed: {exc}", "error")
    return redirect(url_for("items"))


@app.route("/orders")
def orders():
    reset_query_results()
    return render_template("orders.html", orders=get_order_details())


@app.post("/orders/delete")
@admin_required
def delete_order():
    order_id = request.form["order_id"].strip()

    try:
        if not order_id:
            raise ValueError("Order ID cannot be empty.")

        db = get_db()
        if not is_postgres():
            db.execute("BEGIN IMMEDIATE")

        order = fetch_one("SELECT order_id, item_id FROM orders WHERE order_id = ?", (order_id,))
        if order is None:
            raise ValueError("Order does not exist.")

        item_id = order["item_id"]
        execute_write("DELETE FROM orders WHERE order_id = ?", (order_id,), commit=False)
        execute_write("UPDATE item SET status = 0 WHERE item_id = ?", (item_id,), commit=False)
        commit_db()
        flash(f"Order {order_id} was deleted and item {item_id} was marked unsold.", "success")
    except Exception as exc:
        rollback_db()
        flash(f"Delete failed: {exc}", "error")
    return redirect(url_for("orders"))


query_results: dict[str, dict[str, object]] = {}
custom_result: dict[str, object] | None = None
custom_error: dict[str, str] | None = None


@app.route("/queries")
def queries():
    return render_template(
        "queries.html",
        query_definitions=get_query_definitions(),
        query_results=query_results,
        custom_result=custom_result,
        custom_error=custom_error,
    )


@app.post("/queries/run")
def run_preset_query():
    global query_results
    query_id = request.form.get("query_id", "").strip()
    definitions = get_query_definitions()
    target = next((q for q in definitions if q["id"] == query_id), None)
    if target is None:
        flash("Query does not exist.", "error")
        return redirect(url_for("queries"))

    try:
        result = execute_safe_query(target["sql"])
        query_results[query_id] = result
        return render_template(
            "queries.html",
            query_definitions=definitions,
            query_results=query_results,
            custom_result=custom_result,
            custom_error=custom_error,
        )
    except ValueError as exc:
        flash(str(exc), "error")
        return redirect(url_for("queries"))


@app.post("/queries/custom")
def run_custom_query():
    global custom_result, custom_error
    custom_sql = request.form.get("custom_sql", "").strip()
    definitions = get_query_definitions()
    if not custom_sql:
        flash("Please enter a SQL statement.", "error")
        return redirect(url_for("queries"))

    try:
        result = execute_safe_query(custom_sql)
        custom_result = {"sql": custom_sql, **result}
        custom_error = None
        return render_template(
            "queries.html",
            query_definitions=definitions,
            query_results=query_results,
            custom_result=custom_result,
            custom_error=custom_error,
        )
    except ValueError as exc:
        flash(str(exc), "error")
        custom_error = {"sql": custom_sql, "error": str(exc)}
        custom_result = None
        return render_template(
            "queries.html",
            query_definitions=definitions,
            query_results=query_results,
            custom_result=custom_result,
            custom_error=custom_error,
        )


@app.post("/reset")
@admin_required
def reset_database():
    try:
        if is_postgres():
            reset_postgres_data()
        else:
            close_db(None)
            init_database(force=True)
        flash("Database was reset to the initial seed data.", "success")
    except Exception as exc:
        rollback_db()
        flash(f"Reset failed: {exc}", "error")
    return redirect(url_for("index"))


if __name__ == "__main__":
    ensure_database()
    open_browser_later("http://127.0.0.1:5000")
    print("SecondHandSQL is running")
    print("=" * 60)
    print("Local: http://127.0.0.1:5000")
    print(f"Runtime directory: {RUNTIME_DIR}")
    print("=" * 60)
    app.run(host="127.0.0.1", port=5000, debug=False)
