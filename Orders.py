class Orders():
    def __init__(self):
        super().__init__()

    @staticmethod
    def openOrder(mysql, tableNumber, customersNumber):
        cursor = mysql.connection.cursor()
        cursor.execute(f"INSERT INTO pub_tables (table_number, customers_quantity, table_status) VALUES ({tableNumber}, {customersNumber}, 'OPEN');")
        cursor.execute(f"UPDATE pub_lounge SET availability = 'BUSY' WHERE table_number = {tableNumber};")
        mysql.connection.commit()
        cursor.close()
        
    @staticmethod
    def closeOrder(mysql, table_number):
        cursor = mysql.connection.cursor()
        cursor.execute(f"UPDATE pub_tables SET table_status = 'CLOSED' WHERE table_number = {table_number} AND table_status = 'OPEN';")
        cursor.execute(f"SELECT * FROM pub_tables WHERE table_number = {table_number};")
        result = cursor.fetchall()
        print(result)
        for i in result:
            price = i[4]
        cursor.execute(f"UPDATE pub_lounge SET availability = 'FREE' WHERE table_number = {table_number};")
        mysql.connection.commit()
        cursor.close()
        return {
            "price": price
        }

    @staticmethod
    def show_order(mysql, table_number):
        cursor = mysql.connection.cursor()
        cursor.execute(f"SELECT * FROM pub_tables WHERE table_number = {table_number} and table_status = 'OPEN';")
        res = cursor.fetchall()
        cursor.close()
        return res

    @staticmethod
    def list_menu(mysql):
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT drink_id, drink_name, price FROM drinks;")
        res = cursor.fetchall()
        cursor.close()
        return res

    def show_opened_orders(mysql):
        cursor = mysql.connection.cursor()
        result = cursor.execute("SELECT * FROM pub_tables WHERE table_status = 'OPEN';")
        for row in result:
            table_number = row[1]
            people = row[2]
        cursor.close()
        return {
            table_number,
            people
        }

    @staticmethod
    def add_product(mysql, choice, quantity, id):
        cursor = mysql.connection.cursor()
        cursor.execute(f"SELECT * FROM drinks WHERE drink_name = '{choice}'")
        result = cursor.fetchall()
        for row in result:
            name = row[1]

        for i in range(quantity):
            cursor.execute(f"""UPDATE pub_tables
                SET ordered_items =
                    CASE
                        WHEN ordered_items IS NULL THEN '{name}'
                        ELSE CONCAT(ordered_items, ',{name}')
                    END
                WHERE id = {id}""")
            mysql.connection.commit()
        filtered_data = [item for item in result[0] if item is not None]
        for i in range(2, len(filtered_data) - 2, 2):
            cursor.execute(f"UPDATE ingredients SET quantity = quantity - {filtered_data[i+1]*quantity} WHERE ingredient_name = '{filtered_data[i]}';")
            mysql.connection.commit()
        cursor.execute(f"UPDATE pub_tables SET bill = bill + {filtered_data[-1] * quantity} WHERE id = {id};")
        mysql.connection.commit()
        cursor.close()