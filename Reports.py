from flask import jsonify
from mailer import send_email

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
            SELECT o.order_id, o.table_id, o.order_time, o.status, o.customers_number, u.name AS employee,
                   IFNULL(SUM(oi.quantity * d.price), 0) AS total,
                       GROUP_CONCAT(CONCAT(d.drink_name, ' x', oi.quantity) SEPARATOR ', ') AS items
            FROM orders o
            LEFT JOIN order_items oi ON o.order_id = oi.order_id
            LEFT JOIN drinks d ON oi.drink_id = d.drink_id
            LEFT JOIN users u ON o.employee_id = u.user_id
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
        # po uzupełnieniu konkretnego składnika:
        cursor.execute("""
            UPDATE ingredients
            SET low_stock_notified = CASE WHEN stock_quantity >= reorder_level THEN 0 ELSE low_stock_notified END
            WHERE ingredient_id = %s
        """, (ingredient_id,))
        mysql.connection.commit()
        cursor.close()
        return True
    
    @staticmethod
    def checkAllStocks(mysql):
        cursor = mysql.connection.cursor()
        # weź wszystkie poniżej progu i nie zgłoszone
        cursor.execute("""
            SELECT ingredient_id, ingredient_name, stock_quantity, reorder_level
            FROM ingredients
            WHERE stock_quantity < reorder_level AND low_stock_notified = 0
        """)
        low = cursor.fetchall()

        if not low:
            cursor.close()
            return {"ok": True, "notified": 0}

        # zbierz adminów
        cursor.execute("SELECT email FROM users WHERE role='admin' AND email IS NOT NULL")
        admins = cursor.fetchall()
        recipients = [ (a["email"] if isinstance(a, dict) else a[0]) for a in admins or [] ]

        # wyślij zbiorczy mail
        lines = []
        ids = []
        for r in low:
            name = r["ingredient_name"] if isinstance(r, dict) else r[1]
            qty  = r["stock_quantity"]  if isinstance(r, dict) else r[2]
            thr  = r["reorder_level"]   if isinstance(r, dict) else r[3]
            iid  = r["ingredient_id"]   if isinstance(r, dict) else r[0]
            ids.append(iid)
            lines.append(f"- {name}: {qty} (próg {thr})")

        subject = "[Pub Manager] Składniki poniżej progu"
        body = "Poniższe składniki spadły poniżej progu:\n\n" + "\n".join(lines)
        try:
            send_email(subject, recipients, body)
        except Exception as e:
            print("MAIL ERROR:", e)

        # ustaw flagi, aby nie spamować
        if ids:
            fmt = ",".join(["%s"] * len(ids))
            cursor.execute(f"""
                UPDATE ingredients
                SET low_stock_notified = 1, last_notified_at = NOW()
                WHERE ingredient_id IN ({fmt})
            """, tuple(ids))
            mysql.connection.commit()

        cursor.close()
        return {"ok": True, "notified": len(ids)}
