import codecs
import logging
import json
import re
from enum import Enum, unique
from pathlib import Path

PLAYER_CARDS_PATH = Path(r"player_cards.json")
OTHER_CARDS_PATH = Path(r"other_cards.json")
FAQS_PATH = Path(r"faqs")
PROCESSED_DATA_PATH = Path(r'processed_data.json')

NB_PATTERN = re.compile(
    r"\*\*NB:\*\* ArkhamDB now incorporates errata from the Arkham Horror FAQ in its card text, so the ArkhamDB text and the card image above differ, as the ArkhamDB text has been edited to contain this erratum \(updated .+?\):\s?")

# FAQ_PATTERN = re.compile(r"(FAQ),\sv\.(\d+\.\d+),\s(\w+\s\d{4})$")
FAQ_PATTERN = re.compile(r"(FAQ),\sv\.(\d+\.\d+),\s(\w+\s\d{4})")


@unique
class EntryType(str, Enum):
    ERRATUM = "erratum"
    QUESTION_ANSWER = "question/answer"
    CLARIFICATION = "clarification"


def parse_text(text):
    source_type = version = date = None

    # Find all FAQ references in the text
    faq_references = re.findall(FAQ_PATTERN, text)

    # Loop over all FAQ references
    for faq_reference in faq_references:
        # Extract the source type, version, and date from the match
        source_type, version, date = faq_reference

        # Remove the matched string from the text
        text = re.sub(FAQ_PATTERN, "", text)

    # Strip leading and trailing whitespace from the text
    text = text.strip()

    logging.info(f"Processed text: {text}")
    logging.info(f"Extracted source type: {source_type}, version: {version}, date: {date}")

    return text, source_type, version, date

def load_card_names(*card_files):
    return {
        card_code: card_details.get('name', 'Unknown Card')
        for cards_file in card_files
        for set_value in json.load(open(cards_file, 'r', encoding='utf-8-sig')).values()
        for card_type_value in set_value.values()
        for card_code, card_details in card_type_value.items()
    }


def process_ruling(ruling, item_code):
    logging.info(f"Original ruling: {ruling}")

    # Remove strikethrough text in Markdown and HTML
    ruling = re.sub(r"~~.*?~~|<s>.*?</s>|<strike>.*?</strike>", "", ruling)

    ruling, source_type, version, date = parse_text(ruling)
    if not ruling.strip():  # Skip rulings that only contain an FAQ reference
        logging.warning(f"Ruling is empty: {ruling} for card {item_code}")

    ruling = NB_PATTERN.sub("", ruling)
    # ruling = ruling.encode('unicode_escape').decode('utf-8')

    ruling = ruling.replace(r"\*", r"\\*").replace(r"\_", r"\\_")

    ruling = ruling.replace("<b>", "**").replace("</b>", "**")  # Replace HTML bold tags with Markdown
    ruling = ruling.replace("<i>", "*").replace("</i>", "*")  # Replace HTML italic tags with Markdown
    ruling = ruling.replace("\\n", "")  # Strip newline characters

    if not ruling:
        return None

    # If the ruling text contains '**OVERRULED SEE BELOW**', discard the ruling
    if '**OVERRULED SEE BELOW**' in ruling:
        return None

    # Remove '**UPDATE:** ' from the ruling text
    ruling = ruling.replace('**UPDATE:** ', '')

    entry_type = categorize_entry(ruling)
    if entry_type == EntryType.QUESTION_ANSWER:
        split_text = ruling.split("**A:**")
        question = split_text[0].strip("**Q:**").replace('\\"', "").strip()
        ruling = ""
        answer = split_text[1].replace('\\"', "").strip() if len(split_text) > 1 else ""
    elif entry_type == EntryType.ERRATUM:
        question = ""
        answer = ""
        ruling = ruling.replace("**Erratum:**", "").strip()
    else:
        question = ""
        answer = ""
    source = {
        "updated": date,
        "type": source_type,
        "version": version
    }
    return {
        "type": entry_type,
        "content": {"text": ruling, "question": question, "answer": answer},
        "source": source,
        "card_name": card_names.get(item_code, "Unknown Card"),
        "card_code": item_code,
    }

def process_json_file(file_path, card_names):
    try:
        with open(file_path, 'r') as file:
            data = json.load(file)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logging.error(f"Error reading file {file_path}: {e}")
        return {}

    processed_data = {}
    for item in data:
        try:
            text = item["text"]
            rulings = re.split(r"- (?!\bFAQ\b)", text)[1:]  # Split the text by "- " not followed by "FAQ"  # Split the text by "- " to get a list of rulings
            rulings_list = []
            for ruling in rulings:
                if ruling := process_ruling(ruling, item.get('code')):
                    rulings_list.append(ruling)
            processed_data[card_names.get(item.get('code'), "Unknown Card")] = rulings_list
        except Exception as e:
            logging.error(f"Error processing item {item}: {e}")

    return processed_data


def categorize_entry(text):
    patterns = {
        "**Erratum:**": EntryType.ERRATUM,
        "**Q:**": EntryType.QUESTION_ANSWER
    }
    return next((entry_type for pattern, entry_type in patterns.items() if pattern in text), EntryType.CLARIFICATION)


card_names = load_card_names(PLAYER_CARDS_PATH, OTHER_CARDS_PATH)

all_processed_data = {}
for file_path in FAQS_PATH.glob('*.json'):
    all_processed_data |= process_json_file(file_path, card_names)

with open(PROCESSED_DATA_PATH, 'w', encoding='utf-8') as f:
    json.dump(all_processed_data, f, indent=4, ensure_ascii=False)
