class Report():
    def __init__(self):
        super().__init__()

    @staticmethod
    def inventory_report(mysql):
        """
        Zwraca listę składników i ich stany.
        """
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT ingredient_id, ingredient_name, stock_quantity FROM ingredients ORDER BY ingredient_name;")
        res = cursor.fetchall()
        cursor.close()
        return res

    @staticmethod
    def orders_report(mysql):
        """
        Zwraca listę zamówień z ich łączną wartością.
        """
        cursor = mysql.connection.cursor()
        cursor.execute("""
            SELECT o.order_id, o.table_id, o.order_time, o.status,
                   IFNULL(SUM(oi.quantity * d.price), 0) AS total,
                       GROUP_CONCAT(CONCAT(d.drink_name, ' x', oi.quantity) SEPARATOR ', ') AS items
            FROM orders o
            LEFT JOIN order_items oi ON o.order_id = oi.order_id
            LEFT JOIN drinks d ON oi.drink_id = d.drink_id
            GROUP BY o.order_id
            ORDER BY o.order_time DESC;
        """)
        res = cursor.fetchall()
        cursor.close()
        return res

    @staticmethod
    def add_ingredient(mysql, quantity, ingredient_id):
        """
        Dodaje quantity do stock_quantity dla ingredient_id.
        """
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT ingredient_id FROM ingredients WHERE ingredient_id = %s", (ingredient_id,))
        if not cursor.fetchone():
            cursor.close()
            return False
        cursor.execute("UPDATE ingredients SET stock_quantity = stock_quantity + %s WHERE ingredient_id = %s", (quantity, ingredient_id))
        mysql.connection.commit()
        cursor.close()
        return True
