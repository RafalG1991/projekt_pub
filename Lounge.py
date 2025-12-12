class Lounge():
    def __init__(self):
        super().__init__()

    @staticmethod
    def getTables(mysql):
        """
        Zwraca wszystkie stoliki razem z informacją o lounge (jeśli chcemy).
        """
        cursor = mysql.connection.cursor()
        # Pobierz stoliki
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
    
    @staticmethod
    def getLounges(mysql):
        cursor = mysql.connection.cursor()
        cursor.execute("""
            SELECT lounge_id, name
            FROM pub_lounge
            ORDER BY name;
        """)
        res = cursor.fetchall()
        cursor.close()
        return res
    
    @staticmethod
    def getTablesByLounge(mysql, loungeId):
        cursor = mysql.connection.cursor()
        cursor.execute("""
            SELECT pt.table_id, pt.table_number, pt.capacity, pt.table_status,
                   pl.lounge_id, pl.name AS lounge_name
            FROM pub_tables pt
            JOIN pub_lounge pl ON pt.lounge_id = pl.lounge_id
            WHERE pl.lounge_id = %s
            ORDER BY pt.table_number;
        """, (loungeId,))
        res = cursor.fetchall()
        cursor.close()
        return res
    
    @staticmethod
    def getLoungeById(mysql, loungeId):
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT lounge_id, name FROM pub_lounge WHERE lounge_id = %s LIMIT 1;", (loungeId,))
        res = cursor.fetchone()
        cursor.close()
        return res
