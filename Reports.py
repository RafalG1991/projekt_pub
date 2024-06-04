class Report():
    def __init__(self):
        super().__init__()

    @staticmethod
    def inventory_report(mysql):
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM ingredients")
        res = cursor.fetchall()
        cursor.close()
        return res
    
    @staticmethod
    def orders_report(mysql):
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM pub_tables")
        res = cursor.fetchall()
        cursor.close()
        return res

    @staticmethod
    def add_ingredient(mysql, quantity, id):
        cursor = mysql.connection.cursor()
        cursor.execute(f"UPDATE ingredients SET quantity = quantity + {quantity} WHERE ingredient_id = '{id}';")
        mysql.connection.commit()
        cursor.close()



