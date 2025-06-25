from pathlib import Path
import re

# --- Project Root ---
# Assuming constants.py is in src/abyssal_tome/
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# --- Directories ---
ASSETS_DIR = PROJECT_ROOT / "assets"
FAQS_DIR = PROJECT_ROOT / "faqs"
SCHEMAS_DIR = ASSETS_DIR / "schemas"
INDEX_DIR = PROJECT_ROOT / "indexdir" # For Whoosh index

# --- File Paths ---
FAQS_FILE_PATH = FAQS_DIR / "faqs.json"

# Output file paths for processed data
PROCESSED_RULINGS_V2_PATH = ASSETS_DIR / "processed_rulings_v2.json"
PROCESSED_RULINGS_V3_AI_PATH = ASSETS_DIR / "processed_rulings_v3_ai_enriched.json"
RAW_EXTERNAL_RULINGS_PATH = ASSETS_DIR / "raw_external_rulings.json"
OPINIONATED_RULINGS_PATH = ASSETS_DIR / "opinionated_rulings.json"
OLD_PROCESSED_DATA_PATH = ASSETS_DIR / "processed_data.json" # Original processed data for main.py

# Schema files
RULING_SCHEMA_JSON = SCHEMAS_DIR / "ruling_schema.json"
OPINION_SCHEMA_JSON = SCHEMAS_DIR / "opinion_schema.json"

# Old data paths (relative to project root, assuming scripts run from root or handle paths appropriately)
OLD_PLAYER_CARDS_PATH = PROJECT_ROOT / "player_cards.json"
OLD_OTHER_CARDS_PATH = PROJECT_ROOT / "other_cards.json"
OLD_FAQS_DIR_PATH_PROCESS_JSON = FAQS_DIR # For process_json.py that globs this dir


# --- Constants for scripts/process_new_format.py ---
RULING_REMOVAL_PATTERNS: list[str] = [
    "FAQ removed - double-checking provenance.",
    "OVERRULED SEE BELOW",
    "SEE BELOW",
    'Matt writes: "This was unintentional and we are looking into fixing this, perhaps in the next edition of the FAQ."',
    "A: [NB see follow-up Q]",
]

RULING_STRIP_PATTERNS: list[str] = [
    "NB: ArkhamDB now incorporates errata from the Arkham Horror FAQ in its card text, so the ArkhamDB text and the card image above differ, as the ArkhamDB text has been edited to contain this erratum (updated August 2022): ",
    '"As If": This was added to the FAQ (v.1.7, March 2020) and then amended (v.1.8, October 2020). You can read the October ruling on the ArkhamDB rules page here. (I\'m adding a hyperlink rather than retyping the rules in case in future the ruling is changed or amended - at that point, the rules page will be updated and all ArkhamDB FAQ entries will link to the correct ruling.)',
]

# Regex patterns from process_new_format.py
FAQ_VERSION_PATTERN = re.compile(r"(FAQ|Official FAQ|Errata Sheet)[,\s]*v?\.?\s*(\d+\.\d+[\w\d.-]*)\s*,\s*([\w\s]+\s\d{4})", re.IGNORECASE)
CARD_LINK_PATTERN = re.compile(r"(?:arkhamdb\.com)?/card/(\d{5})")

# --- Constants for Icon/Symbol Replacements (used in process_new_format.py and app.py) ---
TAG_TO_LETTER: dict[str, str] = {
    "willpower": "p", "agility": "a", "combat": "c", "intellect": "b",
    "skull": "k", "cultist": "l", "tablet": "q", "elderthing": "n",
    "autofail": "m", "eldersign": "o", "bless": "v", "curse": "w",
    "frost": "x", "reaction": "!", "unique": "s", "mystic": "g",
    "guardian": "f", "seeker": "h", "rogue": "d", "survivor": "e",
    "free": "j", "action": "i",
}


# --- Constants for scripts/enrich_rulings_ai.py ---
DEFAULT_SOURCE_CARD_CODE_EXTERNAL = "00000"


# --- Constants for scripts/scrape_arkhamdb_faq.py ---
# Regex patterns for replacing HTML elements
SPAN_RULE_PATTERN = re.compile(r'<span class="icon-([^"]+)"( title="[^"]*")?></span>')
NEWLINE_RULE_PATTERN = re.compile(r'\r\n')
CARD_LINK_RULE_PATTERN = re.compile(r'http(s?)://arkhamdb\.com/card/')
RULES_LINK_RULE_PATTERN = re.compile(r'http(s?)://arkhamdb.com/rules#')
PARAGRAPH_RULE_PATTERN = re.compile(r'<p>')
CLOSE_PARAGRAPH_RULE_PATTERN = re.compile(r'</p>')

# Dictionary mapping cycle codes to their names
CYCLES_MAP: dict[str, str] = {
    '01': 'core', '02': 'dwl', '03': 'ptc', '04': 'tfa', '05': 'tcu',
    '06': 'tde', '07': 'tic', '08': 'eoe', '09': 'tsk', '50': 'rtnotz',
    '51': 'rtdwl', '52': 'rtptc', '53': 'rttfa', '54': 'rttcu',
    '60': 'investigator', '61': 'investigator', '62': 'investigator',
    '63': 'investigator', '64': 'investigator', '81': 'standalone',
    '82': 'standalone', '83': 'standalone', '84': 'standalone',
    '85': 'standalone', '86': 'standalone', '90': 'parallel', '98': 'books', '99': 'promo',
}

# --- Constants for scripts/process_json.py (old script, for completeness if ever needed) ---
OLD_PLAYER_CARDS_PATH = Path("../player_cards.json") # Assuming relative to scripts/
OLD_OTHER_CARDS_PATH = Path("../other_cards.json")  # Assuming relative to scripts/
OLD_FAQS_DIR_PATH = Path("../faqs")                 # Assuming relative to scripts/
OLD_PROCESSED_DATA_PATH = Path('../assets/processed_data.json') # Assuming relative to scripts/

# Add other general constants here if they arise
# For example, output file paths for processed data could also be constants:
PROCESSED_RULINGS_V2_PATH = Path("../assets/processed_rulings_v2.json")
PROCESSED_RULINGS_V3_AI_PATH = Path("../assets/processed_rulings_v3_ai_enriched.json")
RAW_EXTERNAL_RULINGS_PATH = Path("../assets/raw_external_rulings.json")
OPINIONATED_RULINGS_PATH = Path("../assets/opinionated_rulings.json")
GENERATED_SCHEMAS_DIR = Path("../assets/schemas") # Restoring this line

# Note: TEXT_TO_RULING_TYPE and TAG_TO_LETTER are kept in process_new_format.py
# as they are tightly coupled with the RulingType Enum and specific logic within that script.
# Moving RulingType enum here could create circular dependencies if other scripts also need it
# and this constants file. This setup aims to minimize such issues.
# If RulingType were more general, it could live here.

# --- Flet App specific constants (from main.py/app.py) ---
DEFAULT_FLET_PATH = ""
DEFAULT_FLET_PORT = 8502
```
