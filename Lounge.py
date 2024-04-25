class Lounge():
    def __init__(self):
        super().__init__()

    @staticmethod
    def getTables(mysql):
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM pub_lounge")
        res = cursor.fetchall()
        cursor.close()
        return res

    @staticmethod
    def getAvailableTables(mysql, numberOfGuests):
        cursor = mysql.connection.cursor()
        cursor.execute(f"SELECT * FROM pub_lounge WHERE availability = 'FREE' and capacity >= {numberOfGuests}")
        res = cursor.fetchall()
        cursor.close()
        return res
        
