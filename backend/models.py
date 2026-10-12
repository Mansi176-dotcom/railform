from pydantic import BaseModel, Field
from typing import Literal
VERSION = 'rf-causal-1.0.0'
class Config(BaseModel):
    seed: int = Field(42, ge=1, le=100000)
    speed: float = Field(120, ge=30, le=200)
    noise: float = Field(.08, ge=0, le=.5)
    dropout: float = Field(0, ge=0, le=.5)
    bias: float = Field(0, ge=-2, le=2)
    drift: float = Field(0, ge=0, le=.1)
    severity: float = Field(3, ge=.1, le=8)
    position: float = Field(900, ge=100, le=2900)
    playback: float = Field(10, ge=1, le=30)
    repeated: bool = True
    preset: int = Field(2, ge=0, le=7)
    sample_rate: int = Field(12800, ge=10000, le=25600)
class Workflow(BaseModel):
    status: Literal['New','Acknowledged','Under review','Resolved']
    note: str = Field('', max_length=4000)
