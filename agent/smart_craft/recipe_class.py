from typing import Optional, Any, Union, List

class RawItem:
    def __init__(self, id: int, name: str, count: int = 1, metadata: Any = None):
        self.id = id
        self.name = name
        self.count = count
        self.metadata = metadata

    @classmethod
    def from_dict(cls, d: dict) -> "RawItem":
        if d is None:
            return None
        return cls(
            id=d.get("id"),
            name=d.get("name"),
            count=d.get("count", 1),
            metadata=d.get("metadata")
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "count": self.count,
            "metadata": self.metadata,
        }


class RawRecipe:
    def __init__(
        self,
        result: RawItem,
        ingredients: List[RawItem],
        delta: List[RawItem],
        in_shape: Optional[List[List[Optional[RawItem]]]] = None,
        out_shape: Optional[List[List[Optional[RawItem]]]] = None,
        requires_table: bool = False,
    ):
        self.result = result
        self.ingredients = ingredients or []
        self.delta = delta or []
        self.in_shape = in_shape
        self.out_shape = out_shape
        self.requires_table = requires_table

    @staticmethod
    def _parse_shape(shape: Optional[List[List[Optional[dict]]]]) -> Optional[List[List[Optional[RawItem]]]] :
        if shape is None:
            return None
        parsed: List[List[Optional[RawItem]] ] = []
        for row in shape:
            new_row: List[Optional[RawItem]] = []
            for cell in row:
                if cell is None:
                    new_row.append(None)
                else:
                    new_row.append(RawItem.from_dict(cell))
            parsed.append(new_row)
        return parsed

    @classmethod
    def from_raw_entry(cls, entry: dict) -> "RawRecipe":
        """
        解析单个配方条目，形如：
        {
          "result": {...}, "inShape": ... , "outShape": ...,
          "ingredients": [...], "delta": [...], "requiresTable": false
        }
        """
        result = RawItem.from_dict(entry.get("result"))

        # 解析形状
        in_shape = cls._parse_shape(entry.get("inShape"))
        out_shape = cls._parse_shape(entry.get("outShape"))

        # 解析 delta（仅记录，不用于推导配方需求）
        raw_delta = entry.get("delta") or []
        delta = [RawItem.from_dict(x) for x in (raw_delta if isinstance(raw_delta, list) else [])]

        # 解析 ingredients；尊重原始数据，不进行补全
        raw_ingredients = entry.get("ingredients")
        ingredients: List[RawItem] = []
        if isinstance(raw_ingredients, list) and len(raw_ingredients) > 0:
            ingredients = [RawItem.from_dict(x) for x in raw_ingredients]

        requires_table = bool(entry.get("requiresTable", False))
        return cls(
            result=result,
            ingredients=ingredients,
            delta=delta,
            in_shape=in_shape,
            out_shape=out_shape,
            requires_table=requires_table
        )

    @classmethod
    def from_query_raw_recipe(cls, payload: Union[dict, list]) -> List["RawRecipe"]:
        """
        从工具 `query_raw_recipe` 的返回结构构建配方对象列表。
        支持两种输入：
        - 直接传入单个 entry（含 result/ingredients/...）
        - 传入完整响应：{"ok":true,"data":[entry,...], ...}
        """
        if isinstance(payload, list):
            return [cls.from_raw_entry(e) for e in payload]

        if isinstance(payload, dict):
            data = payload.get("data")
            if isinstance(data, list):
                return [cls.from_raw_entry(e) for e in data]
            # 容错：直接给了单条 entry
            if "result" in payload and "ingredients" in payload:
                return [cls.from_raw_entry(payload)]

        return []

    def to_dict(self) -> dict:
        def shape_to_dict(shape: Optional[List[List[Optional[RawItem]]]]):
            if shape is None:
                return None
            out: List[List[Optional[dict]]] = []
            for row in shape:
                new_row: List[Optional[dict]] = []
                for cell in row:
                    new_row.append(None if cell is None else cell.to_dict())
                out.append(new_row)
            return out

        return {
            "result": self.result.to_dict() if self.result else None,
            "inShape": shape_to_dict(self.in_shape),
            "outShape": shape_to_dict(self.out_shape),
            "ingredients": [x.to_dict() for x in self.ingredients],
            "delta": [x.to_dict() for x in self.delta],
            "requiresTable": self.requires_table,
        }