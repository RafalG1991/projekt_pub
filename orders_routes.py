# orders_routes.py
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from extensions import mysql
from Orders import Orders

orders_bp = Blueprint("orders", __name__, url_prefix="/order")

@orders_bp.post("/open")
@jwt_required()
def open_order():
    # JSON: { tableNumber: int, customersNumber: int }
    data = request.get_json() or {}
    table_number = int(data.get("tableNumber", 0))
    customers = int(data.get("customersNumber", 0))

    ok, msg = Orders.openOrder(mysql, table_number, customers)  # <-- nazwa i argumenty jak w Orders.py
    return jsonify({"ok": bool(ok), "message": msg})

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
@jwt_required()
def show_order(table_number: int):
    res = Orders.show_order(mysql, table_number)  # <-- nazwa 1:1
    return jsonify(res)

@orders_bp.get("/menu")
@jwt_required()
def order_menu():
    res = Orders.list_menu(mysql)  # <-- dokładnie list_menu(mysql)
    return jsonify(res)

@orders_bp.post("/add")
@jwt_required()
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
