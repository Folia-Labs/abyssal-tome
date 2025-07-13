import json
import logging
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.abyssal_tome.models import Provenance, Ruling, RulingDB, Base

# Configure logging
logging.basicConfig(level=logging.INFO)

# --- Main Script ---
def main() -> None:
    """
    Loads FAQ data from a JSON file, processes it into structured ruling objects,
    and writes the results to a SQLite database.
    """
    json_path = Path("assets/processed_rulings_v3_ai_enriched.json")
    db_path = Path("abyssal_tome.db")

    if not json_path.exists():
        logging.error(f"JSON file not found at {json_path}, aborting.")
        return

    engine = create_engine(f"sqlite:///{db_path}")
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        Base.metadata.create_all(engine)
        logging.info("Database tables created.")

        with open(json_path, 'r', encoding='utf-8') as f:
            rulings_data = json.load(f)

        for ruling_dict in rulings_data:
            try:
                ruling = Ruling(**ruling_dict)
                ruling_db = RulingDB(
                    id=ruling.id,
                    source_card_code=ruling.source_card_code,
                    related_card_codes=ruling.related_card_codes,
                    ruling_type=ruling.ruling_type,
                    question=ruling.question,
                    answer=ruling.answer,
                    text=ruling.text,
                    provenance=ruling.provenance.model_dump(),
                    original_html_snippet=ruling.original_html_snippet,
                    tags=ruling.tags,
                )
                session.add(ruling_db)
            except Exception as e:
                logging.error(f"Error processing ruling: {ruling_dict.get('id')}, error: {e}")

        session.commit()
        logging.info(f"Successfully loaded {len(rulings_data)} rulings into {db_path}")

    except Exception as e:
        logging.error(f"An error occurred during database operations: {e}")
        session.rollback()
    finally:
        session.close()
        logging.info("Database session closed.")

if __name__ == "__main__":
    main()
