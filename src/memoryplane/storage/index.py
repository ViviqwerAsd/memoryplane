from __future__ import annotations

import json
from collections import Counter
from math import log
from typing import Any

from memoryplane.models import MemoryRecord
from memoryplane.paths import MemoryPlanePaths
from memoryplane.utils.text import tokenize


class SearchIndexStore:
    def __init__(self, paths: MemoryPlanePaths):
        self.paths = paths

    def initialize(self) -> None:
        if not self.paths.search_cache_file.exists():
            self.save(
                {
                    "version": 1,
                    "documents": {},
                    "doc_freq": {},
                    "avg_doc_length": 0.0,
                }
            )

    def load(self) -> dict[str, Any]:
        self.initialize()
        return json.loads(self.paths.search_cache_file.read_text())

    def save(self, payload: dict[str, Any]) -> None:
        self.paths.search_cache_file.parent.mkdir(parents=True, exist_ok=True)
        self.paths.search_cache_file.write_text(json.dumps(payload, indent=2))

    def add_memory(self, memory: MemoryRecord) -> None:
        payload = self.load()
        documents = payload.setdefault("documents", {})
        tokens = tokenize(memory.content)
        term_freq = Counter(tokens)
        documents[memory.memory_id] = {
            "tokens": tokens,
            "term_freq": dict(term_freq),
            "length": len(tokens),
            "space": memory.space,
            "type": memory.type,
            "entity": memory.entity,
            "timestamp": memory.timestamp,
            "status": memory.status,
        }

        doc_freq: Counter[str] = Counter()
        total_length = 0
        for document in documents.values():
            total_length += document["length"]
            doc_freq.update(set(document["term_freq"].keys()))

        payload["doc_freq"] = dict(doc_freq)
        payload["avg_doc_length"] = total_length / len(documents) if documents else 0.0
        self.save(payload)

    def score(self, query: str, memory: MemoryRecord) -> tuple[float, list[str]]:
        payload = self.load()
        documents = payload.get("documents", {})
        document = documents.get(memory.memory_id)
        if document is None:
            return 0.0, []

        query_terms = tokenize(query)
        if not query_terms:
            return 0.0, []

        term_freq = document["term_freq"]
        doc_freq = payload.get("doc_freq", {})
        doc_count = max(len(documents), 1)
        avg_length = payload.get("avg_doc_length", 0.0) or 1.0
        doc_length = max(document["length"], 1)
        matched_terms: list[str] = []
        score = 0.0
        for term in query_terms:
            tf = term_freq.get(term, 0)
            if not tf:
                continue
            matched_terms.append(term)
            df = doc_freq.get(term, 0)
            idf = log(1 + ((doc_count - df + 0.5) / (df + 0.5)))
            numerator = tf * 2.2
            denominator = tf + 1.2 * (1 - 0.75 + 0.75 * (doc_length / avg_length))
            score += idf * (numerator / denominator)
        return score, matched_terms
