import re
import hashlib
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field, ConfigDict, field_validator

def current_utc_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

class WorkingMemoryItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    key: str = Field(..., min_length=1)
    agent_id: str = Field(..., min_length=1)
    task_id: str = Field(..., pattern=r"^tsk_[0-9a-f]{8,}$")
    data: Dict[str, Any] = Field(default_factory=dict)
    ttl_seconds: Optional[int] = Field(default=3600, ge=1)
    created_at: str = Field(default_factory=current_utc_iso, pattern=r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")

class ProjectMemoryItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(..., pattern=r"^mem_[0-9a-f]{8,}$")
    project_id: str = Field(..., pattern=r"^prj_[0-9a-f]{8,}$")
    key: str = Field(..., min_length=1)
    content: str = Field(..., min_length=1)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    content_sha256: str = Field(..., pattern=r"^[0-9a-f]{64}$")
    importance: float = Field(default=0.5, ge=0.0, le=1.0)
    superseded_by: Optional[str] = Field(default=None, pattern=r"^mem_[0-9a-f]{8,}$")
    commit_sha: Optional[str] = Field(default=None, pattern=r"^[0-9a-f]{7,40}$")
    created_at: str = Field(default_factory=current_utc_iso, pattern=r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")

    @field_validator("content_sha256", mode="before")
    @classmethod
    def compute_or_verify_sha(cls, v: Optional[str], info: Any) -> str:
        if v:
            return v
        # Derive the integrity hash from the content supplied in the same model
        # input instead of silently hashing empty bytes.
        content = (info.data or {}).get("content", "")
        return hashlib.sha256(str(content).encode("utf-8")).hexdigest()

class EngagementMemoryItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(..., pattern=r"^mem_[0-9a-f]{8,}$")
    project_id: str = Field(..., pattern=r"^prj_[0-9a-f]{8,}$")
    engagement_id: str = Field(..., pattern=r"^eng_[0-9a-f]{8,}$")
    scan_id: Optional[str] = Field(default=None, pattern=r"^scn_[0-9a-f]{8,}$")
    key: str = Field(..., min_length=1)
    content: str = Field(..., min_length=1)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    content_sha256: str = Field(..., pattern=r"^[0-9a-f]{64}$")
    importance: float = Field(default=0.5, ge=0.0, le=1.0)
    created_at: str = Field(default_factory=current_utc_iso, pattern=r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")

class KnowledgeMemoryItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(..., pattern=r"^mem_[0-9a-f]{8,}$")
    project_id: str = Field(..., pattern=r"^prj_[0-9a-f]{8,}$")
    key: str = Field(..., min_length=1)
    content: str = Field(..., min_length=1)
    skill_ref: Optional[str] = None
    category: Optional[str] = None
    embedding: Optional[List[float]] = None
    content_sha256: str = Field(..., pattern=r"^[0-9a-f]{64}$")
    importance: float = Field(default=0.5, ge=0.0, le=1.0)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=current_utc_iso, pattern=r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")

    @field_validator("embedding")
    @classmethod
    def validate_embedding_dim(cls, v: Optional[List[float]]) -> Optional[List[float]]:
        if v is not None and len(v) != 384:
            raise ValueError(f"Vector embedding must have exactly 384 dimensions, got {len(v)}")
        return v

class RemediationMemoryItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(..., pattern=r"^mem_[0-9a-f]{8,}$")
    project_id: str = Field(..., pattern=r"^prj_[0-9a-f]{8,}$")
    finding_id: Optional[str] = Field(default=None, pattern=r"^fnd_[0-9a-f]{8,}$")
    key: str = Field(..., min_length=1)
    content: str = Field(..., min_length=1)
    patch_diff: Optional[str] = None
    regression_passed: bool = Field(default=True)
    is_negative_knowledge: bool = Field(default=False)
    content_sha256: str = Field(..., pattern=r"^[0-9a-f]{64}$")
    importance: float = Field(default=0.5, ge=0.0, le=1.0)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=current_utc_iso, pattern=r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
