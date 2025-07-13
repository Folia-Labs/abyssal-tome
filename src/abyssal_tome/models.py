from sqlalchemy import Column, String, JSON, Text
from sqlalchemy.orm import declarative_base
from pydantic import BaseModel
from typing import List, Optional

Base = declarative_base()

class RulingDB(Base):
    __tablename__ = 'rulings'

    id = Column(String, primary_key=True, index=True)
    source_card_code = Column(String, nullable=False)
    related_card_codes = Column(JSON, nullable=False)
    ruling_type = Column(String, nullable=False)
    question = Column(Text)
    answer = Column(Text)
    text = Column(Text)
    provenance = Column(JSON, nullable=False)
    original_html_snippet = Column(Text)
    tags = Column(JSON, nullable=False)

class Provenance(BaseModel):
    source_type: str
    source_name: Optional[str] = None
    source_date: Optional[str] = None
    retrieval_date: str
    source_url: Optional[str] = None

class Ruling(BaseModel):
    id: str
    source_card_code: str
    related_card_codes: List[str]
    ruling_type: str
    question: Optional[str] = None
    answer: Optional[str] = None
    text: Optional[str] = None
    provenance: Provenance
    original_html_snippet: Optional[str] = None
    tags: List[str]

    class Config:
        orm_mode = True
