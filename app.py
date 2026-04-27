from __future__ import annotations

import base64
import io
import socket
import sqlite3
import sys
import threading
import webbrowser
from contextlib import closing
from datetime import date
from pathlib import Path

import qrcode
from flask import Flask, flash, g, redirect, render_template, request, url_for


if getattr(sys, "frozen", False):
    RESOURCE_DIR = Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
    RUNTIME_DIR = Path(sys.executable).resolve().parent
else:
    RESOURCE_DIR = Path(__file__).resolve().parent
    RUNTIME_DIR = RESOURCE_DIR

DATABASE_PATH = RUNTIME_DIR / "secondhandsql.db"
SCHEMA_PATH = RESOURCE_DIR / "schema.sql"
INIT_DATA_PATH = RESOURCE_DIR / "init_data.sql"


app = Flask(
    __name__,
    template_folder=str(RESOURCE_DIR / "templates"),
    static_folder=str(RESOURCE_DIR / "static"),
)
app.config["SECRET_KEY"] = "secondhandsql-demo-secret"
app.config["TEMPLATES_AUTO_RELOAD"] = True


def get_local_ip() -> str:
    try:
        with closing(socket.socket(socket.AF_INET, socket.SOCK_DGRAM)) as sock:
            sock.connect(("8.8.8.8", 80))
            return sock.getsockname()[0]
    except OSError:
        return "127.0.0.1"


def open_browser_later(url: str, delay: float = 1.0) -> None:
    def _open() -> None:
        try:
            webbrowser.open(url)
        except OSError:
            pass

    threading.Timer(delay, _open).start()


def generate_qr_ascii(url: str) -> str:
    """生成 ASCII 二维码用于控制台显示"""
    qr = qrcode.QRCode()
    qr.add_data(url)
    qr.make(fit=True)
    
    f = io.StringIO()
    qr.print_ascii(out=f)
    f.seek(0)
    return f.read()


def generate_qr_image_base64(url: str) -> str:
    """生成 base64 编码的二维码图片用于网页显示"""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(url)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    img_str = base64.b64encode(buffer.getvalue()).decode()
    
    return f"data:image/png;base64,{img_str}"


def get_db() -> sqlite3.Connection:
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
    if not DATABASE_PATH.exists():
        init_database()


def fetch_all(query: str, params: tuple = ()) -> list[sqlite3.Row]:
    return get_db().execute(query, params).fetchall()


def get_dashboard_stats() -> dict[str, str]:
    db = get_db()
    total_items = db.execute("SELECT COUNT(*) AS count FROM item").fetchone()["count"]
    unsold_items = db.execute(
        "SELECT COUNT(*) AS count FROM item WHERE status = 0"
    ).fetchone()["count"]
    total_orders = db.execute(
        "SELECT COUNT(*) AS count FROM orders"
    ).fetchone()["count"]
    total_users = db.execute("SELECT COUNT(*) AS count FROM user").fetchone()["count"]
    average_price = db.execute(
        "SELECT ROUND(AVG(price), 2) AS value FROM item"
    ).fetchone()["value"]
    return {
        "商品总数": str(total_items),
        "未售商品": str(unsold_items),
        "订单总数": str(total_orders),
        "用户总数": str(total_users),
        "平均价格": f"{average_price or 0:.2f}",
    }


def get_items_with_seller() -> list[sqlite3.Row]:
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
        JOIN user AS u ON u.user_id = i.seller_id
        ORDER BY i.item_id
        """
    )


def get_order_details() -> list[sqlite3.Row]:
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
        JOIN user AS u ON u.user_id = o.buyer_id
        ORDER BY o.order_date, o.order_id
        """
    )


def get_query_definitions() -> list[dict[str, object]]:
    return [
        {
            "id": "basic1",
            "title": "基本查询 1：所有未售出的商品",
            "sql": """SELECT item_id, item_name, category, price, seller_id
FROM item
WHERE status = 0
ORDER BY item_id;""",
            "columns": ["item_id", "item_name", "category", "price", "seller_id"],
        },
        {
            "id": "basic2",
            "title": "基本查询 2：价格大于 30 的商品",
            "sql": """SELECT item_id, item_name, price
FROM item
WHERE price > 30
ORDER BY price DESC, item_id;""",
            "columns": ["item_id", "item_name", "price"],
        },
        {
            "id": "basic3",
            "title": "基本查询 3：生活用品类商品",
            "sql": """SELECT item_id, item_name, category, price
FROM item
WHERE category = 'DailyGoods'
ORDER BY item_id;""",
            "columns": ["item_id", "item_name", "category", "price"],
        },
        {
            "id": "basic4",
            "title": "基本查询 4：u001 发布的所有商品",
            "sql": """SELECT item_id, item_name, category, price, status
FROM item
WHERE seller_id = 'u001'
ORDER BY item_id;""",
            "columns": ["item_id", "item_name", "category", "price", "status"],
        },
        {
            "id": "join1",
            "title": "连接查询 1：所有已售商品及其买家姓名",
            "sql": """SELECT
    i.item_id,
    i.item_name,
    o.buyer_id,
    u.user_name AS buyer_name
FROM item AS i
JOIN orders AS o ON o.item_id = i.item_id
JOIN user AS u ON u.user_id = o.buyer_id
WHERE i.status = 1
ORDER BY i.item_id;""",
            "columns": ["item_id", "item_name", "buyer_id", "buyer_name"],
        },
        {
            "id": "join2",
            "title": "连接查询 2：每个订单的商品名、买家名和日期",
            "sql": """SELECT
    o.order_id,
    i.item_name,
    u.user_name AS buyer_name,
    o.order_date
FROM orders AS o
JOIN item AS i ON i.item_id = o.item_id
JOIN user AS u ON u.user_id = o.buyer_id
ORDER BY o.order_date, o.order_id;""",
            "columns": ["order_id", "item_name", "buyer_name", "order_date"],
        },
        {
            "id": "join3",
            "title": "连接查询 3：卖家为 u001 的商品是否被购买",
            "sql": """SELECT
    i.item_id,
    i.item_name,
    CASE
        WHEN o.order_id IS NULL THEN '否'
        ELSE '是'
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
            "title": "聚合 1：商品总数",
            "sql": """SELECT COUNT(*) AS total_items FROM item;""",
            "columns": ["total_items"],
        },
        {
            "id": "agg2",
            "title": "聚合 2：每类商品数量",
            "sql": """SELECT category, COUNT(*) AS item_count
FROM item
GROUP BY category
ORDER BY category;""",
            "columns": ["category", "item_count"],
        },
        {
            "id": "agg3",
            "title": "聚合 3：所有商品平均价格",
            "sql": """SELECT ROUND(AVG(price), 2) AS average_price FROM item;""",
            "columns": ["average_price"],
        },
        {
            "id": "agg4",
            "title": "聚合 4：发布商品数量最多的用户",
            "sql": """SELECT
    u.user_id,
    u.user_name,
    COUNT(i.item_id) AS item_count
FROM user AS u
LEFT JOIN item AS i ON i.seller_id = u.user_id
GROUP BY u.user_id, u.user_name
ORDER BY item_count DESC, u.user_id
LIMIT 1;""",
            "columns": ["user_id", "user_name", "item_count"],
        },
        {
            "id": "view1",
            "title": "视图 1：已售商品视图",
            "sql": """SELECT item_id, item_name, buyer_id
FROM sold_items_view
ORDER BY item_id;""",
            "columns": ["item_id", "item_name", "buyer_id"],
        },
        {
            "id": "view2",
            "title": "视图 2：未售商品视图",
            "sql": """SELECT item_id, item_name, category, price, seller_id
FROM unsold_items_view
ORDER BY item_id;""",
            "columns": ["item_id", "item_name", "category", "price", "seller_id"],
        },
    ]


def execute_safe_query(sql: str) -> dict[str, object]:
    upper_sql = sql.strip().upper()
    forbidden_keywords = [
        "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE",
        "TRUNCATE", "REPLACE", "ATTACH", "DETACH", "PRAGMA",
        "LOAD_EXTENSION",
    ]
    for keyword in forbidden_keywords:
        if keyword in upper_sql:
            raise ValueError(f"禁止执行包含 {keyword} 的语句，只允许 SELECT 查询。")

    if not upper_sql.startswith("SELECT"):
        raise ValueError("只允许执行 SELECT 查询语句。")

    db = get_db()
    try:
        cursor = db.execute(sql)
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description] if cursor.description else []
        return {"columns": columns, "rows": rows}
    except sqlite3.Error as exc:
        raise ValueError(f"SQL 执行错误：{exc}")


def generate_order_id(db: sqlite3.Connection) -> str:
    rows = db.execute("SELECT order_id FROM orders").fetchall()
    max_number = 0
    for row in rows:
        digits = "".join(ch for ch in row["order_id"] if ch.isdigit())
        if digits:
            max_number = max(max_number, int(digits))
    return f"o{max_number + 1:03d}"


def purchase_item(item_id: str, buyer_id: str, order_id: str, order_date: str) -> None:
    db = get_db()
    try:
        db.execute("BEGIN IMMEDIATE")
        item = db.execute(
            "SELECT item_id, status FROM item WHERE item_id = ?",
            (item_id,),
        ).fetchone()
        if item is None:
            raise ValueError("商品不存在。")
        if item["status"] == 1:
            raise ValueError("该商品已售出，不能重复购买。")

        updated = db.execute(
            "UPDATE item SET status = 1 WHERE item_id = ? AND status = 0",
            (item_id,),
        )
        if updated.rowcount != 1:
            raise ValueError("商品状态更新失败。")

        db.execute(
            """
            INSERT INTO orders (order_id, item_id, buyer_id, order_date)
            VALUES (?, ?, ?, ?)
            """,
            (order_id, item_id, buyer_id, order_date),
        )
        db.commit()
    except Exception:
        db.rollback()
        raise


@app.before_request
def ensure_database_before_request() -> None:
    ensure_database()


def reset_query_results() -> None:
    """切换页面时重置查询结果"""
    global query_results, custom_result, custom_error
    query_results = {}
    custom_result = None
    custom_error = None


@app.route("/")
def index():
    reset_query_results()
    local_ip = get_local_ip()
    lan_url = f"http://{local_ip}:5000"
    return render_template(
        "index.html",
        stats=get_dashboard_stats(),
        local_ip=local_ip,
        qr_image=generate_qr_image_base64(lan_url),
    )


@app.route("/users")
def users():
    reset_query_results()
    return render_template(
        "users.html",
        users=fetch_all("SELECT user_id, user_name, phone FROM user ORDER BY user_id"),
    )


@app.post("/users/add")
def add_user():
    user_id = request.form["user_id"].strip()
    user_name = request.form["user_name"].strip()
    phone = request.form["phone"].strip()

    try:
        if not user_id:
            raise ValueError("用户 ID 不能为空。")
        if not user_id.startswith("u"):
            raise ValueError("用户 ID 必须以 u 开头，如 u005。")
        if not user_id[1:].isdigit():
            raise ValueError("用户 ID 格式错误，应为 u + 数字，如 u005。")
        if not user_name:
            raise ValueError("用户名不能为空。")
        validate_phone(phone)

        get_db().execute(
            "INSERT INTO user (user_id, user_name, phone) VALUES (?, ?, ?)",
            (user_id, user_name, phone),
        )
        get_db().commit()
        flash(f"用户 {user_id} ({user_name}) 已成功新增。", "success")
    except (sqlite3.IntegrityError, ValueError) as exc:
        flash(f"新增失败：{exc}", "error")
    return redirect(url_for("users"))


@app.post("/users/update-phone")
def update_user_phone():
    user_id = request.form["user_id"].strip()
    phone = request.form["phone"].strip()

    try:
        if not user_id:
            raise ValueError("用户 ID 不能为空。")
        validate_phone(phone)

        cursor = get_db().execute(
            "UPDATE user SET phone = ? WHERE user_id = ?",
            (phone, user_id),
        )
        get_db().commit()
        if cursor.rowcount == 0:
            flash("修改失败：用户不存在。", "error")
        else:
            flash(f"用户 {user_id} 的手机号已更新。", "success")
    except (sqlite3.IntegrityError, ValueError) as exc:
        flash(f"修改失败：{exc}", "error")
    return redirect(url_for("users"))


@app.post("/users/delete")
def delete_user():
    user_id = request.form["user_id"].strip()

    try:
        if not user_id:
            raise ValueError("用户 ID 不能为空。")

        db = get_db()
        # 检查用户是否有关联的商品或订单
        item_count = db.execute(
            "SELECT COUNT(*) as cnt FROM item WHERE seller_id = ?",
            (user_id,),
        ).fetchone()["cnt"]
        order_count = db.execute(
            "SELECT COUNT(*) as cnt FROM orders WHERE buyer_id = ?",
            (user_id,),
        ).fetchone()["cnt"]

        if item_count > 0:
            raise ValueError(f"该用户发布了 {item_count} 件商品，无法删除。")
        if order_count > 0:
            raise ValueError(f"该用户有 {order_count} 个订单，无法删除。")

        db.execute("DELETE FROM user WHERE user_id = ?", (user_id,))
        db.commit()
        flash(f"用户 {user_id} 已删除。", "success")
    except (sqlite3.IntegrityError, ValueError) as exc:
        flash(f"删除失败：{exc}", "error")
    return redirect(url_for("users"))


@app.route("/items")
def items():
    reset_query_results()
    users_list = fetch_all("SELECT user_id, user_name FROM user ORDER BY user_id")
    items_list = get_items_with_seller()
    unsold_items = [row for row in items_list if row["status"] == 0]
    return render_template(
        "items.html",
        items=items_list,
        users=users_list,
        unsold_items=unsold_items,
        suggested_order_id=generate_order_id(get_db()),
        today=date.today().isoformat(),
    )


def validate_item_id(item_id: str) -> None:
    if not item_id:
        raise ValueError("商品 ID 不能为空。")
    if not item_id.startswith("i"):
        raise ValueError("商品 ID 必须以 i 开头，如 i001。")
    if not item_id[1:].isdigit():
        raise ValueError("商品 ID 格式错误，应为 i + 数字，如 i001。")


def validate_order_id(order_id: str) -> None:
    if not order_id:
        raise ValueError("订单 ID 不能为空。")
    if not order_id.startswith("o"):
        raise ValueError("订单 ID 必须以 o 开头，如 o001。")
    if not order_id[1:].isdigit():
        raise ValueError("订单 ID 格式错误，应为 o + 数字，如 o001。")


def validate_price(price_str: str) -> float:
    try:
        price = float(price_str)
    except ValueError:
        raise ValueError("价格必须是有效数字。")
    if price < 0:
        raise ValueError("价格不能为负数。")
    if price > 999999.99:
        raise ValueError("价格超出允许范围（最大 999999.99）。")
    return price


def validate_phone(phone: str) -> None:
    if not phone:
        raise ValueError("手机号不能为空。")
    if not phone.isdigit():
        raise ValueError("手机号只能包含数字。")
    if len(phone) != 11:
        raise ValueError("手机号必须为 11 位数字。")


@app.post("/items/add")
def add_item():
    item_id = request.form["item_id"].strip()
    item_name = request.form["item_name"].strip()
    category = request.form["category"].strip()
    seller_id = request.form["seller_id"].strip()
    price_str = request.form["price"].strip()

    try:
        validate_item_id(item_id)
        if not item_name:
            raise ValueError("商品名称不能为空。")
        if not category:
            raise ValueError("商品分类不能为空。")
        price = validate_price(price_str)

        db = get_db()
        # 验证用户是否存在
        user = db.execute("SELECT user_id FROM user WHERE user_id = ?", (seller_id,)).fetchone()
        if user is None:
            raise ValueError(f"卖家 {seller_id} 不存在，请先前往用户列表新增用户。")

        db.execute(
            """
            INSERT INTO item (item_id, item_name, category, price, status, seller_id)
            VALUES (?, ?, ?, ?, 0, ?)
            """,
            (item_id, item_name, category, price, seller_id),
        )
        db.commit()
        flash(f"商品 {item_id} 已成功新增。", "success")
    except (sqlite3.IntegrityError, ValueError) as exc:
        flash(f"新增失败：{exc}", "error")
    return redirect(url_for("items"))


@app.post("/items/update-price")
def update_price():
    item_id = request.form["item_id"].strip()
    price_str = request.form["price"].strip()

    try:
        validate_item_id(item_id)
        price = validate_price(price_str)

        cursor = get_db().execute(
            "UPDATE item SET price = ? WHERE item_id = ?",
            (price, item_id),
        )
        get_db().commit()
        if cursor.rowcount == 0:
            flash("改价失败：商品不存在。", "error")
        else:
            flash(f"商品 {item_id} 的价格已更新。", "success")
    except (sqlite3.IntegrityError, ValueError) as exc:
        flash(f"改价失败：{exc}", "error")
    return redirect(url_for("items"))


@app.post("/items/delete")
def delete_item():
    item_id = request.form["item_id"].strip()
    try:
        validate_item_id(item_id)
    except ValueError as exc:
        flash(f"删除失败：{exc}", "error")
        return redirect(url_for("items"))

    db = get_db()
    item = db.execute(
        "SELECT status FROM item WHERE item_id = ?",
        (item_id,),
    ).fetchone()
    if item is None:
        flash("删除失败：商品不存在。", "error")
        return redirect(url_for("items"))
    if item["status"] == 1:
        flash("删除失败：已售商品不能删除。", "error")
        return redirect(url_for("items"))

    db.execute("DELETE FROM item WHERE item_id = ?", (item_id,))
    db.commit()
    flash(f"商品 {item_id} 已删除。", "success")
    return redirect(url_for("items"))


@app.post("/items/purchase")
def buy_item():
    item_id = request.form["item_id"].strip()
    buyer_id = request.form["buyer_id"].strip()
    order_id = request.form["order_id"].strip() or generate_order_id(get_db())
    order_date = request.form["order_date"].strip() or date.today().isoformat()

    try:
        validate_item_id(item_id)
        validate_order_id(order_id)

        db = get_db()
        # 验证买家是否存在
        user = db.execute("SELECT user_id FROM user WHERE user_id = ?", (buyer_id,)).fetchone()
        if user is None:
            raise ValueError(f"买家 {buyer_id} 不存在，请先前往用户列表新增用户。")

        purchase_item(item_id, buyer_id, order_id, order_date)
        flash(
            f"购买成功：订单 {order_id} 已创建，商品 {item_id} 已标记为已售出。",
            "success",
        )
    except (sqlite3.IntegrityError, ValueError) as exc:
        flash(f"购买失败：{exc}", "error")
    return redirect(url_for("items"))


@app.route("/orders")
def orders():
    reset_query_results()
    return render_template("orders.html", orders=get_order_details())


@app.post("/orders/delete")
def delete_order():
    order_id = request.form["order_id"].strip()
    item_id = request.form["item_id"].strip()

    try:
        if not order_id:
            raise ValueError("订单 ID 不能为空。")

        db = get_db()
        # 验证订单是否存在
        order = db.execute(
            "SELECT order_id, item_id FROM orders WHERE order_id = ?",
            (order_id,),
        ).fetchone()
        if order is None:
            raise ValueError("订单不存在。")

        # 显式事务：删除订单并恢复商品状态
        db.execute("BEGIN IMMEDIATE")
        try:
            db.execute("DELETE FROM orders WHERE order_id = ?", (order_id,))
            db.execute(
                "UPDATE item SET status = 0 WHERE item_id = ?",
                (item_id,),
            )
            db.commit()
        except Exception:
            db.rollback()
            raise

        flash(f"订单 {order_id} 已删除，商品 {item_id} 已恢复为未售状态。", "success")
    except (sqlite3.IntegrityError, ValueError) as exc:
        flash(f"删除失败：{exc}", "error")
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
        flash("查询不存在。", "error")
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
        flash("请输入 SQL 语句。", "error")
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
def reset_database():
    close_db(None)
    init_database(force=True)
    flash("数据库已重置为初始数据。", "success")
    return redirect(url_for("index"))


if __name__ == "__main__":
    ensure_database()
    local_ip = get_local_ip()
    lan_url = f"http://{local_ip}:5000"
    open_browser_later("http://127.0.0.1:5000")
    print("校园二手交易平台数据库系统已启动")
    print("=" * 60)
    print("本机访问: http://127.0.0.1:5000")
    print(f"局域网访问: {lan_url}")
    print(f"运行目录: {RUNTIME_DIR}")
    print("=" * 60)
    print("\n手机扫码访问（局域网）:")
    print(generate_qr_ascii(lan_url))
    print("\n提示：如果手机无法访问，请检查 Windows 防火墙是否允许 5000 端口")
    print("=" * 60)
    app.run(host="0.0.0.0", port=5000, debug=False)
