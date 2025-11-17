# orders_routes.py
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from extensions import mysql
from Orders import Orders

orders_bp = Blueprint("orders", __name__, url_prefix="/order")

@orders_bp.post("/open")
@jwt_required()
def open_order():
    # JSON: { tableNumber: int, customersNumber: int , employeeId: int}
    data = request.get_json() or {}
    table_number = int(data.get("tableNumber", 0))
    customers = int(data.get("customersNumber", 0))
    employeeId = int(data.get("employeeId", 0))

    ok, msg = Orders.openOrder(mysql, table_number, customers, employeeId)  # <-- nazwa i argumenty jak w Orders.py
    return jsonify({"ok": bool(ok), "message": msg})

@orders_bp.post("/client/open")
@jwt_required(optional=True)
def open_client_order():
    data = request.get_json() or {}
    table_number = data.get("tableNumber")
    customers_number = data.get("customersNumber", 1)

    if table_number is None:
        return jsonify({"error": "tableNumber required"}), 400

    ok, payload = Orders.openClientOrder(mysql, table_number, customers_number)

    if not ok:
        # rozróżnij 404 dla nieistniejącego stolika, reszta 409-conflict
        if payload.get("error") == "table not found":
            return jsonify(payload), 404
        return jsonify(payload), 409

    return jsonify(payload), 201

@orders_bp.post("/close")
@jwt_required()
def close_order():
    # JSON: { tableNumber: int }
    data = request.get_json() or {}
    table_number = int(data.get("tableNumber", 0))

    res = Orders.close_order(mysql, table_number)  # <-- dokładnie close_order(mysql, table_number)
    # wg Twojego pliku zwraca dict; jeśli tuple, owiń w dict
    return jsonify(res)

@orders_bp.get("/show/<int:table_number>")
@jwt_required(optional=True)
def show_order(table_number: int):
    res = Orders.show_order(mysql, table_number)  # <-- nazwa 1:1
    return jsonify(res)

@orders_bp.get("/menu")
@jwt_required(optional=True)
def order_menu():
    res = Orders.list_menu(mysql)  # <-- dokładnie list_menu(mysql)
    return jsonify(res)

@orders_bp.post("/add")
@jwt_required(optional=True)
def add_item():
    """
    Front wysyła: { id, choice, quantity }
      - w Twoim Orders.py metoda nazywa się add_product(mysql, choice, quantity, table_id)
      - tu mapujemy: id -> table_id
    """
    data = request.get_json() or {}
    table_id = data.get("id")
    choice = data.get("choice")
    quantity = data.get("quantity")

    if table_id is None or not choice or quantity is None:
        return jsonify({"added": "no", "error": "invalid payload"}), 400

    result = Orders.add_product(mysql, choice, int(quantity), int(table_id))  # <-- dokładnie add_product(...)
    # Twoja metoda zwraca "ok" / inne — dopasowujemy format do frontu
    return jsonify({"added": "ok" if result == "ok" else str(result)})


@orders_bp.post("/confirm")
@jwt_required()  # tylko zalogowana obsługa
def confirm_order():
    data = request.get_json() or {}
    table_id = data.get("tableId")
    employee_id = int(data.get("employeeId", 0))

    if table_id is None:
        return jsonify({"error": "tableId required"}), 400

    cursor = mysql.connection.cursor()

    # 1) znajdź PENDING zamówienie dla danego stolika
    cursor.execute("""
        SELECT o.order_id, o.table_id, t.table_number
        FROM orders o
        JOIN pub_tables t ON t.table_id = o.table_id
        WHERE o.table_id = %s AND o.status = 'PENDING'
        ORDER BY o.order_time DESC
        LIMIT 1
    """, (table_id,))
    row = cursor.fetchone()
    if not row:
        cursor.close()
        return jsonify({"error": "pending order not found for this table"}), 404

    order_id = row["order_id"]
    table_id = row["table_id"]  # dla pewności, że mamy właściwe id

    # 2) potwierdź zamówienie i przypisz pracownika
    cursor.execute(
        "UPDATE orders SET status = 'OPEN', employee_id = %s WHERE order_id = %s",
        (employee_id, order_id),
    )

    # 3) ustaw stolik na BUSY
    cursor.execute(
        "UPDATE pub_tables SET table_status = 'BUSY' WHERE table_id = %s",
        (table_id,),
    )

    mysql.connection.commit()
    cursor.close()

    return jsonify({
        "confirmed": True,
        "orderId": order_id,
        "tableId": table_id,
    }), 200


@orders_bp.post("/reject")
@jwt_required()
def reject_order():
    data = request.get_json() or {}
    table_id = data.get("tableId")
    employee_id = int(data.get("employeeId", 0))

    if table_id is None:
        return jsonify({"error": "tableId required"}), 400

    cursor = mysql.connection.cursor()

    # 1) znajdź PENDING zamówienie dla stolika
    cursor.execute("""
        SELECT order_id
        FROM orders
        WHERE table_id = %s AND status = 'PENDING'
        ORDER BY order_time DESC
        LIMIT 1
    """, (table_id,))
    row = cursor.fetchone()

    if not row:
        cursor.close()
        return jsonify({"error": "no pending order for table"}), 404

    order_id = row["order_id"]

    # 2) odrzuć zamówienie
    cursor.execute(
        "UPDATE orders SET status='REJECTED', employee_id=%s WHERE order_id=%s",
        (employee_id, order_id)
    )

    # 3) zwolnij stolik
    cursor.execute(
        "UPDATE pub_tables SET table_status='FREE' WHERE table_id=%s",
        (table_id,)
    )

    mysql.connection.commit()
    cursor.close()

    return jsonify({
        "rejected": True,
        "orderId": order_id,
        "tableId": table_id
    }), 200
