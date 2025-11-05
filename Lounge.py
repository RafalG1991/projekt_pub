class Lounge():
    def __init__(self):
        super().__init__()

    @staticmethod
    def getTables(mysql):
        """
        Zwraca wszystkie stoliki razem z informacją o lounge (jeśli chcemy).
        """
        cursor = mysql.connection.cursor()
        # Pobierz stoliki oraz nazwę lounge (jeśli jest)
        cursor.execute("""
            SELECT pt.table_id, pt.table_number, pt.capacity, pt.table_status, pl.lounge_id, pl.name AS lounge_name
            FROM pub_tables pt
            LEFT JOIN pub_lounge pl ON pt.lounge_id = pl.lounge_id
            ORDER BY pt.table_number;
        """)
        res = cursor.fetchall()
        cursor.close()
        return res

    @staticmethod
    def getAvailableTables(mysql, numberOfGuests):
        """
        Zwraca stoliki które są FREE i mają wystarczającą pojemność.
        """
        cursor = mysql.connection.cursor()
        cursor.execute("""
            SELECT table_id, table_number, capacity, table_status, lounge_id
            FROM pub_tables
            WHERE table_status = 'FREE' AND capacity >= %s
            ORDER BY table_number;
        """, (numberOfGuests,))
        res = cursor.fetchall()
        cursor.close()
        return res
