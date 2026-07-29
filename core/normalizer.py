"""
术语标准化器 —— 将口语化/简称表达映射为规范术语。

基于 terminology.json 构建别名→标准名反向索引，支持：
  - 单个术语标准化
  - 整组实体标准化
"""
from __future__ import annotations
from typing import Any


class TermNormalizer:
    """术语标准化器，维护别名→标准名反向索引。"""

    def __init__(self, terms: dict[str, dict[str, list[str]]]):
        """
        Args:
            terms: 术语词典，{类别: {标准名: [别名列表]}}
        """
        self._index: dict[str, dict[str, str]] = {}  # {类别: {别名: 标准名}}
        self._build_index(terms)

    def _build_index(self, terms: dict[str, dict[str, list[str]]]) -> None:
        """构建别名→标准名反向索引。"""
        semantic_categories = ["部件", "故障或现象", "工艺", "指标"]
        for category in semantic_categories:
            self._index[category] = {}
            cat_terms = terms.get(category, {})
            for standard, aliases in cat_terms.items():
                for alias in aliases:
                    if alias and alias not in self._index[category]:
                        self._index[category][alias] = standard
                # 标准名自身也可查
                if standard and standard not in self._index[category]:
                    self._index[category][standard] = standard

    def normalize_term(self, category: str, raw_term: str) -> str:
        """
        将单个术语标准化。

        Args:
            category: 术语类别（部件/故障或现象/工艺/指标）
            raw_term: 原始表述

        Returns:
            标准术语名，未命中返回空字符串
        """
        idx = self._index.get(category, {})
        if raw_term in idx:
            return idx[raw_term]
        # 模糊回退：检查原始词是否包含或被子串命中
        for alias, standard in idx.items():
            if alias in raw_term or (raw_term and raw_term in alias):
                return standard
        return raw_term

    def normalize_entities(self, raw_entities: dict[str, list[dict[str, str]]]) -> dict[str, list[dict[str, str]]]:
        """
        将一组原始实体标准化。

        Args:
            raw_entities: {字段: [{原始词, 标准词}]}，与提取器输出格式一致

        Returns:
            标准化后的实体，与输入格式相同
        """
        result: dict[str, list[dict[str, str]]] = {}
        semantic_categories = ["部件", "故障或现象", "工艺", "指标"]
        for field, items in raw_entities.items():
            if field in semantic_categories:
                result[field] = [
                    {"原始词": item["原始词"], "标准词": self.normalize_term(field, item["原始词"])}
                    for item in items
                ]
            else:
                result[field] = items
        return result


# 从提取器的角度，标准化已经在提取阶段完成（别名匹配时直接映射到标准名）。
# TermNormalizer 作为独立工具，主要用于：
#   1. 对非词典命中的术语做二次标准化
#   2. 给 LLM 输出做后处理校验
#   3. 跨模块共享标准化逻辑
