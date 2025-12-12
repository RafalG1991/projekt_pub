import os
from flask import Flask, request
from flask_cors import CORS, cross_origin
from flask_mysqldb import MySQL
from dotenv import load_dotenv

load_dotenv()

from Lounge import Lounge
from Orders import Orders
from Reports import Report

app = Flask(__name__)

app.config['CORS_HEADERS'] = 'Content-Type'
app.config['MYSQL_HOST'] = os.getenv("HOST")
app.config['MYSQL_USER'] = os.getenv("USER")
app.config['MYSQL_PASSWORD'] = os.getenv("PASSWORD")
app.config['MYSQL_DB'] = os.getenv("DATABASE")

mysql = MySQL(app)
CORS(app)

# Lounge routes
@app.route("/lounge")
@cross_origin()
def getTabs():
    rv = Lounge.getTables(mysql)
    return {
        "tables": rv
    }

@app.route("/lounge/available/<int:guests>")
@cross_origin()
def getAvailableTabs(guests):
    rv = Lounge.getAvailableTables(mysql, guests)
    return {
        "tables": rv
    }

# Order Routes
@app.route("/order/open", methods=['POST'])
@cross_origin()
def openNewOrder():
    request_json = request.get_json()
    tableNumber = request_json.get('tableNumber')
    customersNumber = request_json.get('customersNumber') 
    success, msg = Orders.openOrder(mysql, tableNumber, customersNumber)
    status = "ok" if success else "error"
    return {
        "status": status,
        "message": msg
    }

@app.route("/order/close", methods=['POST'])
@cross_origin()
def closeThisOrder():
    request_json = request.get_json()
    tableNumber = request_json.get('tableNumber')
    rev = Orders.close_order(mysql, tableNumber)
    return {
        "status": "ok" if rev.get("ok", False) else "error",
        "price": rev.get("price"),
        "message": rev.get("message", "")
    }

@app.route("/order/menu")
@cross_origin()
def openMenuList():
    rv = Orders.list_menu(mysql)
    return {
        "menu": rv
    }

@app.route("/order/show/<int:table>")
@cross_origin()
def showOrder(table):
    rv = Orders.show_order(mysql, table)
    return {
        "order": rv
    }

@app.route("/order/add", methods=['POST'])
@cross_origin()
def addToOrder():
    request_json = request.get_json()
    table_id = request_json.get('id')         
    choice = request_json.get('choice')      
    quantity = request_json.get('quantity')
    rv = Orders.add_product(mysql, choice, quantity, table_id)
    return {
        "added": rv
    }

# Report routes
@app.route("/report/inventory")
@cross_origin()
def getInv():
    rv = Report.inventory_report(mysql)
    return {
        "inv": rv
    }

@app.route("/report/orders")
@cross_origin()
def getOrd():
    rv = Report.orders_report(mysql)
    return {
        "orders": rv
    }

@app.route("/report/add", methods=['POST'])
@cross_origin()
def addIngr():
    request_json = request.get_json()
    id = request_json.get('id')
    quantity = request_json.get('quantity')
    rev = Report.add_ingredient(mysql, quantity, id)
    return {
        "status": "ok" if rev else "error"
    }

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
