import os
import math
import time
import uuid
import hashlib
from typing import Dict, Any, List, Optional, Tuple, Union
from datetime import datetime, timezone

from memory_models import (
    WorkingMemoryItem,
    ProjectMemoryItem,
    EngagementMemoryItem,
    KnowledgeMemoryItem,
    RemediationMemoryItem
)
from database import AegisDatabase

def compute_cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    if not vec1 or not vec2 or len(vec1) != len(vec2):
        return 0.0
    dot_prod = sum(a * b for a, b in zip(vec1, vec2))
    norm1 = math.sqrt(sum(a * a for a in vec1))
    norm2 = math.sqrt(sum(b * b for b in vec2))
    if norm1 == 0.0 or norm2 == 0.0:
        return 0.0
    return dot_prod / (norm1 * norm2)

class MemoryManager:
    def __init__(self, db: Optional[AegisDatabase] = None):
        self.db = db or AegisDatabase()
        self._working_memory: Dict[str, Dict[str, Any]] = {}

    def put_working_memory(self, item: WorkingMemoryItem) -> None:
        self._working_memory[item.key] = {
            "item": item,
            "expires_at": time.time() + (item.ttl_seconds or 3600)
        }

    def get_working_memory(self, key: str) -> Optional[WorkingMemoryItem]:
        entry = self._working_memory.get(key)
        if not entry:
            return None
        if time.time() > entry["expires_at"]:
            del self._working_memory[key]
            return None
        return entry["item"]

    def clear_working_memory_for_task(self, task_id: str) -> int:
        keys_to_remove = [
            k for k, v in self._working_memory.items()
            if v["item"].task_id == task_id
        ]
        for k in keys_to_remove:
            del self._working_memory[k]
        return len(keys_to_remove)

    def store_project_memory(self, item: ProjectMemoryItem) -> Dict[str, Any]:
        return self.db.insert_memory_item(
            mem_id=item.id,
            project_id=item.project_id,
            memory_type="project",
            key=item.key,
            content=item.content,
            content_sha256=item.content_sha256,
            metadata=item.metadata,
            importance=item.importance
        )

    def store_engagement_memory(self, item: EngagementMemoryItem) -> Dict[str, Any]:
        return self.db.insert_memory_item(
            mem_id=item.id,
            project_id=item.project_id,
            scan_id=item.scan_id,
            memory_type="engagement",
            key=item.key,
            content=item.content,
            content_sha256=item.content_sha256,
            metadata=item.metadata,
            importance=item.importance
        )

    def store_knowledge_memory(self, item: KnowledgeMemoryItem) -> Dict[str, Any]:
        meta = dict(item.metadata)
        if item.skill_ref:
            meta["skill_ref"] = item.skill_ref
        if item.category:
            meta["category"] = item.category
        return self.db.insert_memory_item(
            mem_id=item.id,
            project_id=item.project_id,
            memory_type="knowledge",
            key=item.key,
            content=item.content,
            content_sha256=item.content_sha256,
            metadata=meta,
            importance=item.importance,
            embedding=item.embedding
        )

    def store_remediation_memory(self, item: RemediationMemoryItem) -> Dict[str, Any]:
        meta = dict(item.metadata)
        if item.finding_id:
            meta["finding_id"] = item.finding_id
        if item.patch_diff:
            meta["patch_diff"] = item.patch_diff
        meta["regression_passed"] = item.regression_passed
        meta["is_negative_knowledge"] = item.is_negative_knowledge
        return self.db.insert_memory_item(
            mem_id=item.id,
            project_id=item.project_id,
            memory_type="remediation",
            key=item.key,
            content=item.content,
            content_sha256=item.content_sha256,
            metadata=meta,
            importance=item.importance
        )

    def supersede_project_memory(self, old_mem_id: str, new_item: ProjectMemoryItem) -> Dict[str, Any]:
        new_row = self.store_project_memory(new_item)
        self.db.supersede_memory_item(old_mem_id, new_item.id)
        return new_row

    def search_knowledge_by_vector(self, project_id: str, query_embedding: List[float], top_k: int = 5, min_score: float = 0.0, category: Optional[str] = None) -> List[Tuple[Dict[str, Any], float]]:
        if len(query_embedding) != 384:
            raise ValueError(f"Query embedding must have exactly 384 dimensions, got {len(query_embedding)}")
        raw_items = self.db.get_memory_items(project_id, memory_type="knowledge")
        scored = []
        for item in raw_items:
            emb = item.get("embedding")
            if not emb:
                continue
            if category:
                meta = item.get("metadata", {})
                if meta.get("category") != category:
                    continue
            sim = compute_cosine_similarity(query_embedding, emb)
            if sim >= min_score:
                scored.append((item, sim))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]

    def get_memories_by_type(self, project_id: str, memory_type: str) -> List[Dict[str, Any]]:
        return self.db.get_memory_items(project_id, memory_type)
