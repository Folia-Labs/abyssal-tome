import logging
from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy import create_engine, Column, String, JSON, Text
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from pydantic import BaseModel
from typing import List, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)

# --- Database Setup ---
DATABASE_URL = "sqlite:///abyssal_tome.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- SQLAlchemy Model ---
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

# --- Pydantic Models ---
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

# --- FastAPI App ---
app = FastAPI()

# --- Dependency ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- API Endpoints ---
@app.get("/rulings", response_model=List[Ruling])
def get_rulings(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    rulings = db.query(RulingDB).offset(skip).limit(limit).all()
    return rulings

@app.get("/rulings/{ruling_id}", response_model=Ruling)
def get_ruling(ruling_id: str, db: Session = Depends(get_db)):
    ruling = db.query(RulingDB).filter(RulingDB.id == ruling_id).first()
    if ruling is None:
        raise HTTPException(status_code=404, detail="Ruling not found")
    return ruling

@app.get("/search", response_model=List[Ruling])
def search_rulings(query: str, db: Session = Depends(get_db)):
    # A simple search implementation
    search_query = f"%{query}%"
    rulings = db.query(RulingDB).filter(
        (RulingDB.question.like(search_query)) |
        (RulingDB.answer.like(search_query)) |
        (RulingDB.text.like(search_query))
    ).all()
    return rulings
