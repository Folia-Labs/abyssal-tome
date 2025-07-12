import datetime
import json
import logging
import os
from openai import OpenAI
# from typing import List, Dict, Any, Optional # Replaced by built-in types or new syntax
import uuid

# We are working with dictionaries that conform to Ruling/Provenance models
# but won't strictly parse them with Pydantic here to keep this script simpler.
# The Pydantic models are defined in `process_new_format.py`.
from abyssal_tome import constants  # Updated import path
from bs4 import BeautifulSoup  # For stripping HTML if needed from original_html_snippet

logging.basicConfig(level=logging.INFO)
# DEFAULT_SOURCE_CARD_CODE_EXTERNAL is now in constants.py

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

def call_openai_api(prompt: str, model: str = "gpt-4o") -> dict | None:
    """
    Calls the OpenAI API with a given prompt and returns the JSON response.
    """
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a helpful assistant designed to output JSON."},
                {"role": "user", "content": prompt},
            ],
            response_format="json",
        )
        content = response.choices[0].message.content
        if isinstance(content, dict):
            return content
        return json.loads(content)
    except Exception as e:
        logging.error(f"Error calling OpenAI API: {e}")
        return None

# --- Placeholder AI Functions ---


def ai_get_related_cards(
    ruling_text: str, source_card_code: str, existing_related_codes: list[str]
) -> list[str]:
    """
    Identifies related card codes from ruling text using an LLM.
    """
    logging.info(
        f"AI: Identifying related cards for text (source: {source_card_code}): '{ruling_text[:100]}...'"
    )
    prompt = f"""
    Given the following ruling text for the card with code '{source_card_code}', identify any other card codes mentioned in the text.
    Card codes are 5-digit strings.
    Return a JSON object with a single key "related_card_codes" containing a list of the identified card codes.
    Do not include the source card code '{source_card_code}' in the list.

    Ruling text:
    ---
    {ruling_text}
    ---
    """
    response = call_openai_api(prompt)
    if response and "related_card_codes" in response:
        newly_identified_codes = response["related_card_codes"]
        combined_codes = set(existing_related_codes)
        combined_codes.update(newly_identified_codes)
        combined_codes.discard(source_card_code)
        return sorted(list(combined_codes))
    return sorted(list(set(existing_related_codes)))


def ai_extract_provenance_details(
    ruling_text: str, existing_provenance: dict[str, any]
) -> dict[str, any]:
    """
    Extracts detailed provenance information from ruling text using an LLM.
    """
    logging.info(f"AI: Extracting provenance for: '{ruling_text[:100]}...'")
    prompt = f"""
    Given the following ruling text, extract the source name and date.
    The source name is often in the format "FAQ, v.X.Y, Month Year".
    The date should be in ISO 8601 format (YYYY-MM-DD).
    Return a JSON object with "source_name" and "source_date" keys.
    If a value is not found, the corresponding key should have a value of null.

    Ruling text:
    ---
    {ruling_text}
    ---
    """
    response = call_openai_api(prompt)
    updated_provenance = existing_provenance.copy()
    if response:
        if response.get("source_name"):
            updated_provenance["source_name"] = response["source_name"]
        if response.get("source_date"):
            updated_provenance["source_date"] = response["source_date"]
    return updated_provenance


def ai_extract_q_and_a(raw_text: str) -> dict[str, str] | None:
    """
    Extracts a question and answer pair from raw text using an LLM.
    """
    logging.info(f"AI: Extracting Q&A from: '{raw_text[:100]}...'")
    prompt = f"""
    Given the following text, extract the question and answer.
    The text may be prefixed with "Q:" and "A:".
    Return a JSON object with "question" and "answer" keys.
    If the text does not appear to be a question and answer, return null for both keys.

    Text:
    ---
    {raw_text}
    ---
    """
    response = call_openai_api(prompt)
    if response and response.get("question") and response.get("answer"):
        return {
            "question": response["question"],
            "answer": response["answer"],
        }
    return None


def ai_generate_tags(ruling_text: str, existing_tags: list[str]) -> list[str]:
    """
    Generates relevant tags for a ruling based on its text content using an LLM.
    """
    logging.info(f"AI: Generating tags for: '{ruling_text[:100]}...'")
    prompt = f"""
    Given the following ruling text, generate a list of relevant tags.
    Tags should be specific and concise, for example: "timing_window", "cancellation_effect", "enemy_interaction", "player_cards", "mythos_phase".
    Return a JSON object with a single key "tags" containing a list of the generated tags.

    Ruling text:
    ---
    {ruling_text}
    ---
    """
    response = call_openai_api(prompt)
    newly_generated_tags = set()
    if response and "tags" in response:
        newly_generated_tags.update(response["tags"])

    combined_tags = set(existing_tags)
    combined_tags.update(newly_generated_tags)
    return sorted(list(combined_tags))


# --- Conversion for External Rulings ---


def convert_external_ruling_to_standard_format(
    external_ruling: dict[str, any],
) -> dict[str, any] | None:
    """
    Convert a raw external ruling dictionary into a standardized ruling format.

    Attempts to extract provenance details and question/answer structure using AI placeholder functions. Assigns a unique ID, determines the source card code from the text if possible, and sets the ruling type based on whether a Q&A structure is detected. Returns the standardized ruling dictionary, or None if the input lacks required raw text.
    """
    raw_text = external_ruling.get("raw_text")
    if not raw_text:
        logging.warning(
            f"External ruling skipped due to missing raw_text: {external_ruling.get('source_url_or_context')}"
        )
        return None

    # Initial Provenance from external source structure
    provenance = {
        "source_type": external_ruling.get("source_type_hint", "unknown_external"),
        "source_name": None,  # To be filled by AI or manual review
        "source_date": None,  # To be filled by AI or manual review
        "retrieval_date": external_ruling.get(
            "retrieval_date_utc", datetime.datetime.utcnow().isoformat()
        ),
        "source_url": external_ruling.get("source_url_or_context"),
    }

    # Attempt to extract more details from text using AI placeholder
    provenance = ai_extract_provenance_details(raw_text, provenance)

    # Try to structure Q&A
    extracted_qa = ai_extract_q_and_a(raw_text)

    ruling_id = str(uuid.uuid4())
    standard_ruling = {
        "id": ruling_id,
        # Try to find a card code in the raw_text for source_card_code, otherwise use default.
        # This is a very basic placeholder for card association.
        "source_card_code": constants.DEFAULT_SOURCE_CARD_CODE_EXTERNAL,  # Placeholder, AI could improve this
        "related_card_codes": [],  # To be filled by ai_get_related_cards
        "provenance": provenance,
        "original_html_snippet": raw_text,  # Store raw_text as the 'snippet' for external
        "tags": [],  # To be filled by ai_generate_tags
    }

    # Temp: simple check for mentioned card codes in raw_text to assign as source_card_code
    # A real version would use more robust NLP/AI.
    # Example: Look for "[01001]" or "card 01001"
    import re

    card_code_match = re.search(r"\[(\d{5})\]|card (\d{5})", raw_text)
    if card_code_match:
        actual_code = card_code_match.group(1) or card_code_match.group(2)
        standard_ruling["source_card_code"] = actual_code

    if extracted_qa:
        standard_ruling["ruling_type"] = "QUESTION_ANSWER"
        standard_ruling["question"] = extracted_qa["question"]
        standard_ruling["answer"] = extracted_qa["answer"]
        standard_ruling["text"] = None
    else:
        standard_ruling["ruling_type"] = "CLARIFICATION"  # Default for non-Q&A
        standard_ruling["question"] = None
        standard_ruling["answer"] = None
        standard_ruling["text"] = raw_text  # Use full raw text if not Q&A

    return standard_ruling


# --- Main Processing Logic ---


def enrich_rulings(rulings_data: list[dict[str, any]]) -> list[dict[str, any]]:
    """
    Enriches a list of ruling dictionaries with AI-generated metadata such as related card codes, provenance details, question-and-answer extraction, and tags.

    Each ruling is processed to ensure required fields are present, selects the most informative text for AI analysis, and applies AI placeholder functions to update related cards, provenance, Q&A structure, and tags. Rulings lacking suitable text for enrichment are skipped but included in the output.

    Parameters:
        rulings_data (list[dict[str, any]]): List of ruling dictionaries to be enriched.

    Returns:
        list[dict[str, any]]: List of enriched ruling dictionaries with updated metadata.
    """
    enriched_rulings: list[dict[str, any]] = []
    for ruling_dict in rulings_data:
        # Make a copy to avoid modifying the original list of dicts in-place if it's reused
        enriched_ruling = ruling_dict.copy()  # Works淺copy for dicts of primitives/nested dicts

        # Ensure basic structure for provenance if it's somehow missing (e.g. from external)
        if "provenance" not in enriched_ruling:
            enriched_ruling["provenance"] = {}
        if "source_card_code" not in enriched_ruling:  # Should be present from conversion
            enriched_ruling["source_card_code"] = constants.DEFAULT_SOURCE_CARD_CODE_EXTERNAL

        # Determine the best text to send to AI (question+answer, or text)
        text_for_ai = ""
        if enriched_ruling.get("question") and enriched_ruling.get("answer"):
            text_for_ai = f"Q: {enriched_ruling['question']} A: {enriched_ruling['answer']}"
        elif enriched_ruling.get("text"):
            text_for_ai = enriched_ruling["text"]
        elif enriched_ruling.get("original_html_snippet"):
            # For already processed ArkhamDB rulings, original_html_snippet is HTML.
            # For external rulings, it's raw text.
            # We need plain text for AI.
            soup = BeautifulSoup(enriched_ruling["original_html_snippet"], "html.parser")
            text_for_ai = soup.get_text(separator=" ", strip=True)

        if not text_for_ai and enriched_ruling.get(
            "original_html_snippet"
        ):  # Fallback for external that might be plain
            text_for_ai = enriched_ruling["original_html_snippet"]

        if not text_for_ai:
            logging.warning(
                f"Skipping AI enrichment for ruling ID {enriched_ruling.get('id')} due to no text."
            )
            enriched_rulings.append(enriched_ruling)
            continue

        # 1. Card Linkage (applies to all)
        enriched_ruling["related_card_codes"] = ai_get_related_cards(
            text_for_ai,
            enriched_ruling["source_card_code"],
            enriched_ruling.get("related_card_codes", []),
        )

        # 2. Provenance Mining (Example: only if source_type is generic or needs detail)
        # This is a simplistic trigger; real logic would be more nuanced.
        if enriched_ruling.get("provenance", {}).get(
            "source_type"
        ) == "arkhamdb_faq" and not enriched_ruling.get("provenance", {}).get(
            "source_name", ""
        ).startswith("FAQ v"):
            enriched_ruling["provenance"] = ai_extract_provenance_details(
                text_for_ai, enriched_ruling.get("provenance", {})
            )

        # 3. Q&A Extraction (Illustrative: if type is CLARIFICATION but looks like Q&A)
        # This would typically be for *new* raw sources, not already processed ones.
        # For this example, let's assume we might re-evaluate some clarifications.
        if enriched_ruling.get("ruling_type") == "CLARIFICATION":
            extracted_qa = ai_extract_q_and_a(text_for_ai)
            if extracted_qa:
                enriched_ruling["ruling_type"] = "QUESTION_ANSWER"  # Change type
                enriched_ruling["question"] = extracted_qa["question"]
                enriched_ruling["answer"] = extracted_qa["answer"]
                enriched_ruling["text"] = None  # Clear out old text field

        # 4. Tag Generation
        enriched_ruling["tags"] = ai_generate_tags(text_for_ai, enriched_ruling.get("tags", []))

        enriched_rulings.append(enriched_ruling)
    return enriched_rulings


def main() -> None:
    """
    Processes and enriches card ruling data by merging existing processed rulings with external raw rulings, applying AI-based enrichment, and saving the results to an output file.

    Loads processed and external rulings from specified file paths, converts external rulings to a standard format, enriches all rulings with AI-generated metadata, and writes the enriched data to a JSON file. Handles missing files and I/O errors with logging.
    """
    processed_input_path = constants.PROCESSED_RULINGS_V2_PATH
    external_input_path = constants.RAW_EXTERNAL_RULINGS_PATH
    output_path = constants.PROCESSED_RULINGS_V3_AI_PATH

    all_rulings_to_process: list[dict[str, any]] = []

    # Load already processed rulings
    if not processed_input_path.exists():
        logging.warning(
            f"Processed rulings file not found: {processed_input_path}. Starting with empty list."
        )
    else:
        try:
            with processed_input_path.open("r", encoding="utf-8") as f:
                all_rulings_to_process.extend(json.load(f))
            logging.info(
                f"Loaded {len(all_rulings_to_process)} rulings from {processed_input_path}"
            )
        except json.JSONDecodeError as e:
            logging.error(f"Error decoding JSON from {processed_input_path}: {e}")
            return
        except OSError as e:
            logging.error(f"Error reading from {processed_input_path}: {e}")
            return

    # Load and convert external rulings
    if not external_input_path.exists():
        logging.warning(
            f"External rulings file not found: {external_input_path}. No external rulings will be added."
        )
    else:
        try:
            with external_input_path.open("r", encoding="utf-8") as f:
                raw_external_data = json.load(f)
            logging.info(
                f"Loaded {len(raw_external_data)} raw external entries from {external_input_path}"
            )

            converted_external_rulings = []
            for ext_ruling_dict in raw_external_data:
                standardized = convert_external_ruling_to_standard_format(ext_ruling_dict)
                if standardized:
                    converted_external_rulings.append(standardized)

            logging.info(
                f"Converted {len(converted_external_rulings)} external rulings to standard format."
            )
            all_rulings_to_process.extend(converted_external_rulings)

        except json.JSONDecodeError as e:
            logging.error(f"Error decoding JSON from {external_input_path}: {e}")
        except OSError as e:
            logging.error(f"Error reading from {external_input_path}: {e}")

    # Perform AI enrichment on the combined list
    final_rulings = enrich_rulings(all_rulings_to_process)

    try:
        with output_path.open("w", encoding="utf-8") as f:
            json.dump(
                final_rulings, f, indent=2, ensure_ascii=False, default=str
            )  # Add default=str for any non-serializable types like datetime
        logging.info(
            f"Successfully enriched a total of {len(final_rulings)} rulings and saved to {output_path}"
        )
    except OSError as e:
        logging.error(f"Error writing enriched rulings to {output_path}: {e}")


if __name__ == "__main__":
    main()
