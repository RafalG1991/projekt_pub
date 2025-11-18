# orders_routes.py
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
from extensions import mysql, socketio
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
        err = payload.get("error") if isinstance(payload, dict) else str(payload)

        if err == "table not found":
            return jsonify(payload), 404
        if err == "too many guests":
            # 409 Conflict – biznesowo: nie spełnia warunków stolika
            return jsonify(payload), 409

        # inne błędy (table busy/pending itp.)
        return jsonify(payload), 409

     # payload zawiera m.in. table_id i status='PENDING'
    table_id = payload.get("table_id")

    if table_id is not None:
        socketio.emit(
            "table_updated",
            {
                "table_id": table_id,
                "table_number": table_number,
                "table_status": "PENDING",
            },
        )

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
    order_id = data.get("orderId")
    employeeId = int(data.get("employeeId", 0))

    cursor = mysql.connection.cursor()

    if order_id is None and table_id is not None:
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

    if order_id is None:
        cursor.close()
        return jsonify({"error": "orderId or tableId required"}), 400

    cursor.execute("""
        SELECT o.order_id, o.table_id, t.table_number
        FROM orders o
        JOIN pub_tables t ON t.table_id = o.table_id
        WHERE o.order_id = %s AND o.status = 'PENDING'
        LIMIT 1
    """, (order_id,))
    row = cursor.fetchone()
    if not row:
        cursor.close()
        return jsonify({"error": "pending order not found"}), 404

    table_id = row["table_id"]
    table_number = row["table_number"]

    cursor.execute(
        "UPDATE orders SET status = 'OPEN', employee_id = %s WHERE order_id = %s",
        (employeeId, order_id)
    )
    cursor.execute(
        "UPDATE pub_tables SET table_status = 'BUSY' WHERE table_id = %s",
        (table_id,)
    )

    mysql.connection.commit()
    cursor.close()

    # TU emit
    socketio.emit(
        "table_updated",
        {
            "table_id": table_id,
            "table_number": table_number,
            "table_status": "BUSY",
        },
    )

    return jsonify({"confirmed": True, "orderId": order_id}), 200


@orders_bp.post("/reject")
@jwt_required()
def reject_order():
    data = request.get_json() or {}
    table_id = data.get("tableId")
    order_id = data.get("orderId")

    cursor = mysql.connection.cursor()

    if order_id is None and table_id is not None:
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

    if order_id is None:
        cursor.close()
        return jsonify({"error": "orderId or tableId required"}), 400

    cursor.execute(
        "SELECT table_id FROM orders WHERE order_id = %s",
        (order_id,)
    )
    row = cursor.fetchone()
    if not row:
        cursor.close()
        return jsonify({"error": "order not found"}), 404

    table_id = row["table_id"]

    cursor.execute(
        "UPDATE orders SET status = 'REJECTED' WHERE order_id = %s",
        (order_id,)
    )
    cursor.execute(
        "UPDATE pub_tables SET table_status = 'FREE' WHERE table_id = %s",
        (table_id,)
    )

    mysql.connection.commit()
    cursor.close()

    socketio.emit(
        "table_updated",
        {
            "table_id": table_id,
            "table_status": "FREE",
        },
    )

    return jsonify({"rejected": True, "orderId": order_id}), 200

@orders_bp.get("/client/status/<int:tableNumber>")
@jwt_required(optional=True)  # klient bez logowania
def client_order_status(tableNumber):
    cursor = mysql.connection.cursor()
    cursor.execute("""
        SELECT o.order_id, o.status
        FROM orders o
        JOIN pub_tables t ON t.table_id = o.table_id
        WHERE t.table_number = %s
        ORDER BY o.order_time DESC
        LIMIT 1
    """, (tableNumber,))
    row = cursor.fetchone()
    cursor.close()

    if not row:
        return jsonify({"hasOrder": False}), 404

    return jsonify({
        "hasOrder": True,
        "orderId": row["order_id"],
        "status": row["status"],   # 'PENDING', 'OPEN', 'REJECTED', ...
    }), 200

@orders_bp.post("/client/signal")
@jwt_required(optional=True)
def client_signal():
    """
    JSON: { tableNumber: int, type: "WAITER"|"CUTLERY"|"CLEANING" }
    Nic nie zapisuje w DB, tylko wysyła sygnał przez Socket.IO.
    """
    data = request.get_json() or {}
    table_number = data.get("tableNumber")
    signal_type = (data.get("type") or "").upper()

    if not table_number or signal_type not in ("WAITER", "CUTLERY", "CLEANING"):
        return jsonify({"error": "invalid payload"}), 400

    # znajdź table_id (potrzebne frontendowi)
    cursor = mysql.connection.cursor()
    cursor.execute(
        "SELECT table_id FROM pub_tables WHERE table_number=%s",
        (table_number,)
    )
    row = cursor.fetchone()
    cursor.close()

    if not row:
        return jsonify({"error": "table not found"}), 404

    table_id = row["table_id"]

    # wyślij lekki event przez socket
    socketio.emit(
        "table_signal",
        {
            "table_id": table_id,
            "table_number": table_number,
            "type": signal_type,
            "ts": datetime.utcnow().isoformat(),
        },
    )

    return jsonify({"ok": True}), 200