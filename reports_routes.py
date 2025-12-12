# reports_routes.py
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from datetime import datetime, timedelta
from extensions import mysql
from authz import role_required     
from Reports import Report

reports_bp = Blueprint("reports", __name__, url_prefix="/report")

@reports_bp.get("/inventory")
@jwt_required()
@role_required("admin")            
def inventory():
    res = Report.inventory_report(mysql)
    return jsonify({"inventory": res})

@reports_bp.get("/orders")
@jwt_required()
@role_required("admin")             
def orders_report():
    res = Report.orders_report(mysql)
    return jsonify({"orders": res})

@reports_bp.post("/add")
@jwt_required()
@role_required("admin")             
def add_ingr():
    req = request.get_json() or {}
    ing_id = req.get("id")
    qty = req.get("quantity")
    if ing_id is None or qty is None:
        return jsonify({"status": "error", "error": "invalid payload"}), 400
    ok = Report.add_ingredient(mysql, qty, ing_id)
    return jsonify({"status": "ok" if ok else "error"})

@reports_bp.get("/recheck")
@jwt_required()
@role_required("admin")
def recheck_all():
    res = Report.checkAllStocks(mysql)
    return {"notified": res}

def _get_date_range():
    """
    Prosty helper: ?days=7 (domyślnie 30)
    Zwraca (start_date, end_date) jako date()
    """
    try:
        days = int(request.args.get("days", 30))
    except ValueError:
        days = 30
    if days < 1:
        days = 1
    today = datetime.utcnow().date()
    start = today - timedelta(days=days - 1)
    end = today
    return start, end


@reports_bp.route("/summary", methods=["GET", "OPTIONS"])
@jwt_required()
def sales_summary():
    """
    Prosty raport:
    - total_turnover: suma obrotu
    - orders_count: liczba zamówień
    - avg_order_value: średnia wartość zamówienia
    Zakres: ostatnie ?days=, domyślnie 30.
    """
    start, end = _get_date_range()

    cur = mysql.connection.cursor()
    cur.execute(
        """
        SELECT
            COUNT(DISTINCT o.order_id) AS orders_count,
            IFNULL(SUM(oi.quantity * d.price), 0) AS total_turnover
        FROM orders o
        LEFT JOIN order_items oi ON oi.order_id = o.order_id
        LEFT JOIN drinks d ON d.drink_id = oi.drink_id
        WHERE o.status != 'REJECTED'
          AND DATE(o.order_time) BETWEEN %s AND %s
        """,
        (start, end),
    )
    row = cur.fetchone() or {}
    cur.close()

    orders_count = int(row.get("orders_count") or 0)
    total_turnover = float(row.get("total_turnover") or 0.0)
    avg_order_value = total_turnover / orders_count if orders_count > 0 else 0.0

    return jsonify(
        {
            "from": start.isoformat(),
            "to": end.isoformat(),
            "total_turnover": total_turnover,
            "orders_count": orders_count,
            "avg_order_value": avg_order_value,
        }
    )


@reports_bp.route("/popular-items", methods=["GET", "OPTIONS"])
@jwt_required()
def popular_items():
    """
    TOP N pozycji z menu wg ilości + obrotu.
    ?days=   - zakres (domyślnie 30)
    ?limit=5 - ile pozycji (domyślnie 5)
    """
    start, end = _get_date_range()
    try:
        limit = int(request.args.get("limit", 5))
    except ValueError:
        limit = 5
    if limit < 1:
        limit = 1
    if limit > 50:
        limit = 50

    cur = mysql.connection.cursor()
    cur.execute(
        """
        SELECT
            d.drink_id,
            d.drink_name,
            IFNULL(SUM(oi.quantity), 0) AS total_qty,
            IFNULL(SUM(oi.quantity * d.price), 0) AS revenue
        FROM orders o
        JOIN order_items oi ON oi.order_id = o.order_id
        JOIN drinks d ON d.drink_id = oi.drink_id
        WHERE o.status != 'REJECTED'
          AND DATE(o.order_time) BETWEEN %s AND %s
        GROUP BY d.drink_id, d.drink_name
        ORDER BY total_qty DESC, revenue DESC
        LIMIT %s
        """,
        (start, end, limit),
    )
    rows = cur.fetchall() or []
    cur.close()

    items = []
    for r in rows:
        items.append(
            {
                "drink_id": r.get("drink_id"),
                "name": r.get("drink_name"),
                "total_qty": int(r.get("total_qty") or 0),
                "revenue": float(r.get("revenue") or 0.0),
            }
        )

    return jsonify(
        {
            "from": start.isoformat(),
            "to": end.isoformat(),
            "items": items,
        }
    )