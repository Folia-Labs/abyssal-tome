import logging
import os
from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from src.abyssal_tome.models import Provenance, Ruling, RulingDB, Base
from typing import List, Generator

# Configure logging
logging.basicConfig(level=logging.INFO)

# --- Database Setup ---
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///abyssal_tome.db")
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# --- FastAPI App ---
app = FastAPI()

# --- Dependency ---
def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

from fastapi import Query

# --- API Endpoints ---
@app.get("/rulings", response_model=List[Ruling])
def get_rulings(skip: int = Query(0, ge=0), limit: int = Query(20, ge=0), db: Session = Depends(get_db)):
    rulings = db.query(RulingDB).offset(skip).limit(limit).all()
    return rulings

@app.get("/rulings/{ruling_id}", response_model=Ruling)
def get_ruling(ruling_id: str, db: Session = Depends(get_db)) -> Ruling:
    ruling = db.query(RulingDB).filter(RulingDB.id == ruling_id).first()
    if ruling is None:
        raise HTTPException(status_code=404, detail="Ruling not found")
    return ruling

@app.get("/search", response_model=List[Ruling])
def search_rulings(query: str, skip: int = Query(0, ge=0), limit: int = Query(20, ge=0), db: Session = Depends(get_db)):
    # A simple search implementation
    search_query = f"%{query}%"
    rulings = db.query(RulingDB).filter(
        (RulingDB.question.like(search_query)) |
        (RulingDB.answer.like(search_query)) |
        (RulingDB.text.like(search_query)) |
        (RulingDB.original_html_snippet.like(search_query))
    ).offset(skip).limit(limit).all()
    return rulings
