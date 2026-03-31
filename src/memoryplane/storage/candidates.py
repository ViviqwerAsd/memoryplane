from __future__ import annotations

import json

from memoryplane.models import CandidateRecord
from memoryplane.paths import MemoryPlanePaths


class CandidateStore:
    def __init__(self, paths: MemoryPlanePaths):
        self.paths = paths

    def save(self, candidate: CandidateRecord) -> None:
        path = self.paths.candidate_file(candidate.candidate_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(candidate.model_dump(mode="json"), indent=2))

    def load(self, candidate_id: str) -> CandidateRecord | None:
        path = self.paths.candidate_file(candidate_id)
        if not path.exists():
            return None
        return CandidateRecord.model_validate_json(path.read_text())

    def delete(self, candidate_id: str) -> None:
        path = self.paths.candidate_file(candidate_id)
        if path.exists():
            path.unlink()

    def list_candidates(self) -> list[CandidateRecord]:
        if not self.paths.candidates_dir.exists():
            return []
        candidates: list[CandidateRecord] = []
        for path in sorted(self.paths.candidates_dir.glob("*.json")):
            candidates.append(CandidateRecord.model_validate_json(path.read_text()))
        return candidates

    def mark_rejected(self, candidate_id: str) -> CandidateRecord | None:
        candidate = self.load(candidate_id)
        if candidate is None:
            return None
        candidate.status = "rejected"
        self.save(candidate)
        return candidate
