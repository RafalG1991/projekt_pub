from DataBase import DataBase


class Report(DataBase):
    def __init__(self):
        super().__init__()

    def inventory_report(self):
        result = self.data_base_interaction("SELECT * FROM ingredients")
        for row in result:
            print(row)

    def orders_report(self):
        result = self.data_base_interaction("SELECT * FROM pub_tables")
        for row in result:
            print(row)



