"""按明确别名归一化，未知词保持原样，避免子串猜测造成部件混淆。"""
from __future__ import annotations


class TermNormalizer:
    def __init__(self, terms: dict):
        self.index = {}
        for category, values in terms.items():
            self.index[category] = {}
            for standard, aliases in values.items():
                for alias in [standard, *aliases]:
                    key = alias.casefold()
                    previous = self.index[category].get(key)
                    if previous and previous != standard:
                        raise ValueError(f"词典别名冲突：{category}.{alias}")
                    self.index[category][key] = standard

    def normalize_term(self, category: str, raw_term: str) -> str:
        return self.index.get(category, {}).get(raw_term.casefold(), raw_term)

    def normalize_entities(self, entities: dict) -> dict:
        return {field: [
            {"原始词": item["原始词"],
             "标准词": self.normalize_term(field, item["原始词"])
             if item["原始词"].casefold() in self.index.get(field, {}) else item["标准词"]}
            for item in values
        ] for field, values in entities.items()}
