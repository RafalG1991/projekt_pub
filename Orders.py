# Orders.py

def _get(row, key, idx):
    """Zwróć wartość z wiersza niezależnie czy to dict (DictCursor) czy tuple."""
    return row[key] if isinstance(row, dict) else row[idx]

def _col(row, key, idx):
    """Alias (to samo co _get) – używany w list comprehensions itd."""
    return row[key] if isinstance(row, dict) else row[idx]


class Orders:
    def __init__(self):
        super().__init__()

    @staticmethod
    def openOrder(mysql, tableNumber, customersNumber):
        """
        Otwiera nowe zamówienie dla stolika o podanym table_number:
        - sprawdza status stolika (FREE/BUSY)
        - ustawia pub_tables.table_status = 'BUSY'
        - tworzy wpis w orders (status OPEN)
        Zwraca (True, msg) lub (False, msg)
        """
        cursor = mysql.connection.cursor()

        # Pobierz ID i status stołu
        cursor.execute(
            "SELECT table_id, table_status FROM pub_tables WHERE table_number=%s",
            (tableNumber,)
        )
        t = cursor.fetchone()
        if not t:
            cursor.close()
            return False, "table not found"

        table_id = _get(t, "table_id", 0)
        table_status = _get(t, "table_status", 1)

        if table_status == 'BUSY':
            cursor.close()
            return False, "Table already BUSY"

        # Ustaw stolik na BUSY
        cursor.execute(
            "UPDATE pub_tables SET table_status='BUSY' WHERE table_id=%s",
            (table_id,)
        )

        # Utwórz zamówienie
        cursor.execute(
            """
            INSERT INTO orders (table_id, status, customers_number)
            VALUES (%s, 'OPEN', %s)
            """,
            (table_id, customersNumber)
        )

        mysql.connection.commit()
        cursor.close()
        return True, "Order opened"

    @staticmethod
    def close_order(mysql, table_number):
        """
        Zamknij wszystkie OTWARTE zamówienia dla wskazanego stolika.
        Zwróć łączną wartość pozycji (quantity * price) dla zamkniętych zamówień.
        """
        cursor = mysql.connection.cursor()

        # Znajdź table_id
        cursor.execute(
            "SELECT table_id FROM pub_tables WHERE table_number=%s",
            (table_number,)
        )
        t = cursor.fetchone()
        if not t:
            cursor.close()
            return {"ok": False, "message": "table not found"}

        table_id = _col(t, "table_id", 0)

        # Znajdź wszystkie OPEN orders dla stołu
        cursor.execute(
            "SELECT order_id FROM orders WHERE table_id=%s AND status='OPEN'",
            (table_id,)
        )
        orders = cursor.fetchall()
        if not orders:
            cursor.close()
            return {"ok": False, "message": "No open orders for this table", "price": 0}

        order_ids = [_col(row, "order_id", 0) for row in orders]

        # Oblicz łączną cenę
        format_ids = ",".join(["%s"] * len(order_ids))
        cursor.execute(
        f"""
        SELECT COALESCE(SUM(oi.quantity * d.price), 0) AS total_price
        FROM order_items oi
        JOIN drinks d ON oi.drink_id = d.drink_id
        WHERE oi.order_id IN ({format_ids})
        """,
        tuple(order_ids)
        )
        total_row = cursor.fetchone()
        val = _get(total_row, "total_price", 0) if total_row else 0
        total_price = float(val or 0)  

        # Zamknij zamówienia i oznacz stolik jako FREE
        cursor.execute(
            f"UPDATE orders SET status='CLOSED' WHERE order_id IN ({format_ids})",
            tuple(order_ids)
        )
        cursor.execute(
            "UPDATE pub_tables SET table_status='FREE' WHERE table_id=%s",
            (table_id,)
        )

        mysql.connection.commit()
        cursor.close()
        return {"ok": True, "price": total_price}

    @staticmethod
    def show_order(mysql, table_number):
        """
        Pokaż OTWARTE zamówienie(a) dla konkretnego stolika w formacie
        [{ order_id, table_number, customers_number, items, total }, ...]
        """
        cursor = mysql.connection.cursor()

        # Znajdź table_id
        cursor.execute(
            "SELECT table_id FROM pub_tables WHERE table_number=%s",
            (table_number,)
        )
        t = cursor.fetchone()
        if not t:
            cursor.close()
            return {"order": []}

        table_id = _get(t, "table_id", 0)

        query = """
            SELECT 
                o.order_id,
                t.table_number,
                o.customers_number,
                GROUP_CONCAT(CONCAT(d.drink_name, ' x', oi.quantity) SEPARATOR ', ') AS items,
                IFNULL(SUM(oi.quantity * d.price), 0) AS total
            FROM orders o
            LEFT JOIN order_items oi ON o.order_id = oi.order_id
            LEFT JOIN drinks d ON oi.drink_id = d.drink_id
            JOIN pub_tables t ON o.table_id = t.table_id
            WHERE o.table_id = %s AND o.status = 'OPEN'
            GROUP BY o.order_id, t.table_number, o.customers_number
            ORDER BY o.order_id DESC;
        """
        cursor.execute(query, (table_id,))
        rows = cursor.fetchall()

        # Znormalizuj wynik do listy dictów (gdyby cursor był bez DictCursor)
        result = []
        for r in rows or []:
            result.append({
                "order_id": _get(r, "order_id", 0),
                "table_number": _get(r, "table_number", 1),
                "customers_number": _get(r, "customers_number", 2),
                "items": _get(r, "items", 3),
                "total": float(_get(r, "total", 4) or 0),
            })

        cursor.close()
        return {"order": result}

    @staticmethod
    def list_menu(mysql):
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT drink_id, drink_name, price, description FROM drinks;")
        rows = cursor.fetchall()

        # Opcjonalnie znormalizuj na listę obiektów (przydatne dla frontu)
        result = []
        for r in rows or []:
            result.append({
                "drink_id": _get(r, "drink_id", 0),
                "drink_name": _get(r, "drink_name", 1),
                "price": float(_get(r, "price", 2) or 0),
                "description": _get(r, "description", 3),
            })
        cursor.close()
        return {"menu": result}

    @staticmethod
    def add_product(mysql, choice, quantity, table_id):
        """
        Dodaje produkt (drink) do OTWARTEGO zamówienia przypisanego do table_id.
        - choice: nazwa napoju (string) lub id (int lub string cyfr)
        - quantity: int > 0
        - table_id: id stolika (pub_tables.table_id)
        """
        if not quantity or int(quantity) <= 0:
            return "error: invalid quantity"

        cursor = mysql.connection.cursor()

        # 1) znajdź otwarte zamówienie dla table_id
        cursor.execute(
            "SELECT order_id FROM orders WHERE table_id=%s AND status='OPEN' ORDER BY order_time LIMIT 1",
            (table_id,)
        )
        order = cursor.fetchone()
        if not order:
            cursor.close()
            return "error: no open order for table"

        order_id = _col(order, "order_id", 0)

        # 2) znajdź drink (po nazwie lub po id)
        if isinstance(choice, int) or (isinstance(choice, str) and choice.isdigit()):
            cursor.execute(
                "SELECT drink_id, drink_name, price FROM drinks WHERE drink_id=%s",
                (int(choice),)
            )
        else:
            cursor.execute(
                "SELECT drink_id, drink_name, price FROM drinks WHERE drink_name=%s",
                (choice,)
            )
        drink = cursor.fetchone()
        if not drink:
            cursor.close()
            return "error: drink not found"

        drink_id = _get(drink, "drink_id", 0)
        drink_name = _get(drink, "drink_name", 1)  # może się przydać do logów
        drink_price = float(_get(drink, "price", 2) or 0)

        # 3) pobierz wymagane składniki i porównaj ze stanem
        cursor.execute(
            """
            SELECT
                di.ingredient_id,
                i.ingredient_name,
                di.amount * %s AS required_quantity,
                i.stock_quantity
            FROM drink_ingredients di
            JOIN ingredients i ON di.ingredient_id = i.ingredient_id
            WHERE di.drink_id = %s
            """,
            (quantity, drink_id)
        )
        ingredients = cursor.fetchall()

        for ingr in ingredients or []:
            required = float(_get(ingr, "required_quantity", 2) or 0)
            available = float(_get(ingr, "stock_quantity", 3) or 0)
            if required > available:
                cursor.close()
                name = _get(ingr, "ingredient_name", 1)
                return f"error: ingredient {name} insufficient"

        # 4) Zmniejsz stany składników
        for ingr in ingredients or []:
            required = float(_get(ingr, "required_quantity", 2) or 0)
            ingr_id = _get(ingr, "ingredient_id", 0)
            cursor.execute(
                "UPDATE ingredients SET stock_quantity = stock_quantity - %s WHERE ingredient_id = %s",
                (required, ingr_id)
            )

        # 5) Dodaj/aktualizuj pozycję zamówienia
        cursor.execute(
            """
            INSERT INTO order_items (order_id, drink_id, quantity)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE quantity = quantity + VALUES(quantity)
            """,
            (order_id, drink_id, quantity)
        )

        mysql.connection.commit()
        cursor.close()
        return "ok"
