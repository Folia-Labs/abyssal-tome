import json
import logging
from pathlib import Path
from sqlalchemy import create_engine, Column, String, JSON, Text
from sqlalchemy.orm import declarative_base, sessionmaker
from pydantic import BaseModel, Field
from typing import List, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)

# --- Pydantic Models ---
# These models should ideally be in a central location, but for now, we'll redefine them here
# to match the structure of the JSON data.

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

# --- SQLAlchemy Models ---
Base = declarative_base()

class RulingDB(Base):
    __tablename__ = 'rulings'

    id = Column(String, primary_key=True)
    source_card_code = Column(String, nullable=False)
    related_card_codes = Column(JSON, nullable=False)
    ruling_type = Column(String, nullable=False)
    question = Column(Text)
    answer = Column(Text)
    text = Column(Text)
    provenance = Column(JSON, nullable=False)
    original_html_snippet = Column(Text)
    tags = Column(JSON, nullable=False)

# --- Main Script ---
def main():
    # Define paths
    json_path = Path("assets/processed_rulings_v3_ai_enriched.json")
    db_path = Path("abyssal_tome.db")

    # Check if JSON file exists
    if not json_path.exists():
        logging.error(f"JSON file not found at {json_path}")
        return

    # Create engine and session
    engine = create_engine(f"sqlite:///{db_path}")
    Session = sessionmaker(bind=engine)
    session = Session()

    # Create tables
    Base.metadata.create_all(engine)

    # Load data from JSON
    with open(json_path, 'r', encoding='utf-8') as f:
        rulings_data = json.load(f)

    # Process and add data to the database
    for ruling_dict in rulings_data:
        # Validate with Pydantic
        ruling = Ruling(**ruling_dict)

        # Create a RulingDB instance
        ruling_db = RulingDB(
            id=ruling.id,
            source_card_code=ruling.source_card_code,
            related_card_codes=ruling.related_card_codes,
            ruling_type=ruling.ruling_type,
            question=ruling.question,
            answer=ruling.answer,
            text=ruling.text,
            provenance=ruling.provenance.dict(),
            original_html_snippet=ruling.original_html_snippet,
            tags=ruling.tags,
        )
        session.add(ruling_db)

    # Commit the session
    session.commit()
    logging.info(f"Successfully loaded {len(rulings_data)} rulings into {db_path}")

if __name__ == "__main__":
    main()
