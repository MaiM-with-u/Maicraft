from typing import List
class RecipeItem:
    def __init__(self,item_name:str,item_count:int,metadata:str = ""):
        self.item_name = item_name
        self.item_count = item_count
        self.metadata = metadata
    
    def to_json(self):
        return {
            "item_name": self.item_name,
            "item_count": self.item_count,
            "metadata": self.metadata
        }

class Recipe:
    def __init__(self,result: RecipeItem,ingredients: List[RecipeItem],inshape: List[List[RecipeItem]],outshape: List[List[RecipeItem]],requires_table: bool):
        self.result = result
        self.ingredients = ingredients
        self.inshape = inshape
        self.outshape = outshape
        self.requires_table = requires_table

    def to_json(self):
        return {
            "result": self.result.to_json(),
            "ingredients": [item.to_json() for item in self.ingredients],
            "inshape": self.inshape,
            "outshape": self.outshape,
            "requires_table": self.requires_table
        }
        