from DataBase import DataBase


class Inventory(DataBase):
    def __init__(self):
        super().__init__()

    def inventory_update(self):
        name = input("Provide name of drink: ")
        quantity = float(input("Provide quantity: "))
        self.data_base_interaction(f"UPDATE ingredients SET quantity = quantity + {quantity} WHERE ingredient_name = '{name}';")

    def inventory_warning(self):
        result = self.data_base_interaction("SELECT * FROM ingredients WHERE quantity <= 300;")
        for row in result:
            name = row[1]
            quantity = row[2]
            print(f"Ingredient name: {name}   quantity: {quantity}")



