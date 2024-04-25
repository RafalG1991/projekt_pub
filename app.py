from flask import Flask, request
from flask_cors import CORS, cross_origin
from flask_mysqldb import MySQL

from Lounge import Lounge
from Orders import Orders
 
app = Flask(__name__)

app.config['CORS_HEADERS'] = 'Content-Type'
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'pub_db'
 
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

@app.route("/lounge/available/<int:id>")
@cross_origin()
def getAvailableTabs(id):
    rv = Lounge.getAvailableTables(mysql, id)
    print(rv)
    return {
        "tables": rv
    }

#Order Routes
@app.route("/order/open", methods = ['POST'])
@cross_origin()
def openNewOrder():
    request_json = request.get_json()
    tableNumber = request_json.get('tableNumber')
    customersNumber = request_json.get('customersNumber')
    Orders.openOrder(mysql, tableNumber, customersNumber)
    return {
        "status": "ok"
    }