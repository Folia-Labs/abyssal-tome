# from typing import List, Optional, Dict, Any # Replaced by built-in types or new syntax
from pydantic import BaseModel, Field
import datetime
import uuid
import json
import logging
from enum import Enum, StrEnum # Added StrEnum
from pathlib import Path # Added for file operations in loading functions


# --- Data Models reflecting processed_rulings_v3_ai_enriched.json structure ---
# These mirror the Pydantic models in scripts/process_new_format.py for consistency.

class RulingTypeEnum(str, Enum):
    ERRATA = "ERRATA"
    ADDENDUM = "ADDENDUM"
    QUESTION_ANSWER = "QUESTION_ANSWER"
    CLARIFICATION = "CLARIFICATION"
    NOTE = "NOTE"
    UPDATE = "UPDATE"
    AS_IF = "AS_IF"
    AUTOMATIC_SUCCESS_FAILURE = "AUTOMATIC_SUCCESS_FAILURE"
    AUTOMATIC_SUCCESS_FAILURE_AUTOMATIC_EVASION = "AUTOMATIC_SUCCESS_FAILURE_AUTOMATIC_EVASION"
    # This needs to be kept in sync with the RulingType in scripts/process_new_format.py

class ProvenanceModel(BaseModel):
    source_type: str
    source_name: str | None = None
    source_date: str | None = None # Consider converting to datetime on validation if format is consistent
    retrieval_date: str # Should be datetime, or validated string
    source_url: str | None = None

    model_config = {"extra": "forbid"}

class OpinionProvenanceModel(BaseModel):
    author: str
    source_description: str | None = None
    source_url: str | None = None
    date_of_opinion: str | None = None # Consider datetime

    model_config = {"extra": "forbid"}

class OpinionatedRulingModel(BaseModel):
    opinion_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    applies_to_ruling_id: str
    opinion_text: str
    opinion_summary: str | None = None
    provenance: OpinionProvenanceModel
    tags: list[str] = Field(default_factory=list)
    replaces_official_text: bool = False

    model_config = {"extra": "forbid"}

class RulingModel(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source_card_code: str
    related_card_codes: list[str] = Field(default_factory=list)
    ruling_type: RulingTypeEnum
    question: str | None = None
    answer: str | None = None
    text: str | None = None
    provenance: ProvenanceModel
    original_html_snippet: str | None = None
    tags: list[str] = Field(default_factory=list)

    opinions: list[OpinionatedRulingModel] = Field(default_factory=list, exclude=True)

    model_config = {"extra": "forbid"}


# Forward reference resolution for RulingModel.opinions -> OpinionatedRulingModel is usually handled
# by Pydantic V2 if OpinionatedRulingModel is defined before RulingModel, or if type hint is string.
# Explicit model_rebuild is often not needed in V2 for this.

# --- Application-level Data Representation (Example) ---
class CardDisplay:
    """Represents a card and all its associated rulings for display."""
    def __init__(self, code: str, name: str, rulings: list[RulingModel]):
        """
        Initialize a CardDisplay instance with the given card code, name, and a list of rulings.
        
        Rulings are sorted by their provenance source date, with missing dates treated as '0000'.
        """
        self.code = code
        self.name = name
        self.rulings = sorted(rulings, key=lambda r: r.provenance.source_date or '0000')

# Global storage
ALL_RULINGS_DATA: dict[str, RulingModel] = {}
ALL_OPINIONS_DATA: dict[str, list[OpinionatedRulingModel]] = {}
# At the top of src/abyssal_tome/model.py, add:
from typing import Any

# …

# Then, update line 91:
CARD_INFO_DATA: dict[str, dict[str, Any]] = {}


# --- Data Loading Functions ---

def load_card_data(file_path_str: str = "../assets/player_cards.json"): # Added _str suffix
    """
    Placeholder for loading card data from a JSON file.
    
    This function currently does not implement any loading logic and only logs an informational message. Actual card data loading should be implemented as needed.
    """
    global CARD_INFO_DATA
    # file_path = Path(file_path_str) # Uncomment when Path is used
    logging.info(f"Card data loading placeholder from {file_path_str}.")
    # Actual implementation needed based on project's card data files


def load_rulings_data(file_path_str: str = "../assets/processed_rulings_v3_ai_enriched.json"):
    """
    Load and validate rulings data from a JSON file into the global ALL_RULINGS_DATA dictionary.
    
    Reads a list of rulings from the specified file, validates each entry as a RulingModel, and stores them by their ID. Logs errors for validation failures, missing files, or JSON decoding issues.
    """
    global ALL_RULINGS_DATA
    file_path = Path(file_path_str)
    try:
        json_text = file_path.read_text(encoding='utf-8')
        rulings_list_raw = json.loads(json_text)

        loaded_count = 0
        for ruling_dict in rulings_list_raw:
            try:
                ruling_obj = RulingModel.model_validate(ruling_dict)
                ALL_RULINGS_DATA[ruling_obj.id] = ruling_obj
                loaded_count += 1
            except Exception as e:
                logging.error(f"Error validating ruling data for ID {ruling_dict.get('id', 'N/A')}: {e}\nData: {ruling_dict}") # Added N/A default
        logging.info(f"Loaded {loaded_count} rulings from {file_path} into ALL_RULINGS_DATA.")
    except FileNotFoundError:
        logging.error(f"Rulings file not found: {file_path}")
    except json.JSONDecodeError:
        logging.error(f"Error decoding JSON from rulings file: {file_path}")
    except Exception as e:
        logging.error(f"An unexpected error occurred loading rulings: {e}", exc_info=True) # Added exc_info


def load_opinionated_rulings_data(file_path_str: str = "../assets/opinionated_rulings.json"):
    """
    Load opinionated rulings from a JSON file, validate them, and associate them with their corresponding official rulings.
    
    Reads opinionated rulings from the specified file, validates each entry, and groups them by the official ruling ID they reference. Associates validated opinions with their corresponding rulings in the global data store, logging warnings for opinions referencing non-existent rulings. Updates the global opinions mapping with the loaded data.
    """
    global ALL_OPINIONS_DATA, ALL_RULINGS_DATA # ALL_OPINIONS_DATA was not global before
    file_path = Path(file_path_str)
    temp_opinions_map: dict[str, list[OpinionatedRulingModel]] = {}
    try:
        json_text = file_path.read_text(encoding='utf-8')
        opinions_list_raw = json.loads(json_text)

        loaded_count = 0
        for opinion_dict in opinions_list_raw:
            try:
                opinion_obj = OpinionatedRulingModel.model_validate(opinion_dict)
                if opinion_obj.applies_to_ruling_id not in temp_opinions_map: # Corrected applies_to_rulin_id
                    temp_opinions_map[opinion_obj.applies_to_ruling_id] = []
                temp_opinions_map[opinion_obj.applies_to_ruling_id].append(opinion_obj)
                loaded_count +=1
            except Exception as e:
                logging.error(f"Error validating opinionated ruling data for ID {opinion_dict.get('opinion_id', 'N/A')}: {e}\nData: {opinion_dict}") # Added N/A default
        logging.info(f"Loaded {loaded_count} opinionated rulings from {file_path}, mapping to {len(temp_opinions_map)} official ruling IDs.")

        for ruling_id, opinions_for_ruling in temp_opinions_map.items():
            if ruling_id in ALL_RULINGS_DATA:
                sorted_opinions = sorted(opinions_for_ruling, key=lambda o: o.provenance.author or "") # Added or ""
                ALL_RULINGS_DATA[ruling_id].opinions.extend(sorted_opinions)
            else:
                logging.warning(f"Opinionated ruling found for non-existent official ruling ID: {ruling_id}")

        ALL_OPINIONS_DATA = temp_opinions_map

    except FileNotFoundError:
        logging.error(f"Opinionated rulings file not found: {file_path}")
    except json.JSONDecodeError:
        logging.error(f"Error decoding JSON from opinionated rulings file: {file_path}")
    except Exception as e:
        logging.error(f"An unexpected error occurred loading opinionated rulings: {e}", exc_info=True) # Added exc_info

# --- Helper Functions for Application --- # Renamed from "Views"

def get_rulings_for_card(card_code: str) -> list[RulingModel]:
    """
    Retrieve all rulings associated with a given card code, including those where the card is either the source or related.
    
    Parameters:
        card_code (str): The code of the card for which to find relevant rulings.
    
    Returns:
        list[RulingModel]: A list of matching rulings sorted by provenance source date and ruling ID.
    """
    relevant_rulings: dict[str, RulingModel] = {}
    for r_id, r_obj in ALL_RULINGS_DATA.items():
        if r_obj.source_card_code == card_code or card_code in r_obj.related_card_codes:
            relevant_rulings[r_id] = r_obj

    return sorted(list(relevant_rulings.values()), key=lambda r_sort: (r_sort.provenance.source_date or "0", r_sort.id))


def get_ruling_by_id(ruling_id: str) -> RulingModel | None: # Added | None
    """
    Retrieve a ruling by its unique ID.
    
    Returns:
        The RulingModel instance corresponding to the given ruling ID, or None if not found.
    """
    return ALL_RULINGS_DATA.get(ruling_id)

# Placeholder for loading card names, etc.
def load_card_info_data(file_path_str: str = "../assets/cards_db.json"): # Example path
    """
    Placeholder for loading card information data from a JSON file.
    
    This function currently does not implement actual loading logic and only logs the intended file path.
    """
    global CARD_INFO_DATA
    # Example: CARD_INFO_DATA = {"01001": {"name": "Roland Banks", "faction": "Guardian"}}
    # Actual implementation depends on how card data is stored/sourced.
    logging.info(f"Placeholder: Card info data would be loaded from {file_path_str}")

# Initialize data on module load if this script is run, or explicitly by the app
# This is a common pattern for web apps to load data once at startup.
# Consider a dedicated initialization function for clarity in a larger app.
# def initialize_app_data():
#     load_card_info_data()
#     load_rulings_data()
#     load_opinionated_rulings_data()

# if __name__ == "__main__": # Example for direct testing of this module
#     logging.basicConfig(level=logging.INFO)
#     # load_card_data() # Placeholder
#     load_rulings_data()
#     load_opinionated_rulings_data()
#     # Example usage:
#     # test_rulings = get_rulings_for_card("01001") # Example card code
#     # if test_rulings:
#     #     print(f"\nRulings for card 01001:")
#     #     for r in test_rulings:
#     #         print(r.model_dump_json(indent=2, exclude_none=True))
#     #         if r.opinions:
#     #             print(f"  Opinions for {r.id}: {len(r.opinions)}")
#     # else:
#     #     print("No rulings found for card 01001")

if __name__ == "__main__": # Restoring this block
    # This block is for utility functions like schema generation when the script is run directly.
    logging.basicConfig(level=logging.INFO)
    # from pathlib import Path # Path is already imported at the top of the file

    # --- JSON Schema Generation ---
    current_file_path = Path(__file__).resolve()
    project_root = current_file_path.parent
    if project_root.name == "model.py":
        project_root = project_root.parent

    if not (project_root / "assets").is_dir():
        project_root = project_root.parent

    output_dir = project_root / "assets/schemas"

    output_dir.mkdir(parents=True, exist_ok=True)
    logging.info(f"Schema output directory: {output_dir.resolve()}")

    try:
        ruling_schema = RulingModel.model_json_schema()
        schema_file_path = output_dir / "ruling_schema.json"
        with schema_file_path.open("w", encoding="utf-8") as f:
            json.dump(ruling_schema, f, indent=2)
        logging.info(f"Generated ruling_schema.json at {schema_file_path.resolve()}")
    except Exception as e:
        logging.error(f"Error generating ruling_schema.json: {e}", exc_info=True)

    try:
        opinion_schema = OpinionatedRulingModel.model_json_schema()
        schema_file_path = output_dir / "opinion_schema.json"
        with schema_file_path.open("w", encoding="utf-8") as f:
            json.dump(opinion_schema, f, indent=2)
        logging.info(f"Generated opinion_schema.json at {schema_file_path.resolve()}")
    except Exception as e:
        logging.error(f"Error generating opinion_schema.json: {e}", exc_info=True)
# (The trailing
