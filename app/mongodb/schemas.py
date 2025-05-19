from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid

class MoodEntry(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    mood_level: float  # -10 до +10
    emotions: List[Dict[str, Any]]  # список эмоций с интенсивностью
    triggers: Optional[List[str]] = None
    physical_sensations: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)

class ThoughtEntry(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    situation: str
    automatic_thought: str
    initial_belief_level: float  # 0-100%
    emotions: List[Dict[str, Any]]  # список эмоций с интенсивностью
    cognitive_distortions: Optional[List[str]] = None
    supporting_evidence: Optional[List[str]] = None
    contradicting_evidence: Optional[List[str]] = None
    balanced_thought: Optional[str] = None
    final_belief_level: Optional[float] = None  # 0-100%
    action_plan: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)

class StateSnapshot(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    mood: float  # -10 до +10
    energy: float  # -10 до +10
    stress_anxiety: float  # 0-10
    need_satisfaction: Dict[str, float]  # категория потребности -> уровень
    date: datetime
    timestamp: datetime = Field(default_factory=datetime.now)