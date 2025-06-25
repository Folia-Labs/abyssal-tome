import asyncio
import json
import re

import aiohttp
import requests
import tqdm
from tqdm.asyncio import tqdm_asyncio

from abyssal_tome import constants # Updated import path

# Regex patterns and cycles map moved to constants.py


def fetch_cards() -> list[dict[str, any]]:  # Added type hint
    """
    Fetches all encounter cards from the ArkhamDB API.
    
    Returns:
        A list of dictionaries, each representing a card with its associated data.
    """
    uri = "https://arkhamdb.com/api/public/cards/?encounter=1"
    print("Fetching all cards from ArkhamDB.")
    response = requests.get(uri)
    response.raise_for_status()  # Good practice to check for HTTP errors
    cards = response.json()
    print(f"Got {len(cards)} cards")
    return cards


async def fetch_faq(
    session: aiohttp.ClientSession, card: dict[str, any]
) -> dict[str, any] | None:  # Added type hints
    """
    Asynchronously fetches the FAQ data for a given card from the ArkhamDB API.
    
    Returns:
        The parsed FAQ JSON data as a dictionary if successful, or None if the card code is missing or an HTTP error occurs.
    """
    code = card.get("code")
    if not code:
        return None
    faq_uri = f"https://arkhamdb.com/api/public/faq/{code}.json"
    try:
        async with session.get(faq_uri) as response:
            response.raise_for_status()
            return await response.json()
    except aiohttp.ClientError as e:
        print(f"Error fetching FAQ for card {code}: {e}")
        return None


def parse_faqs(faqs: list[dict[str, any] | None]) -> dict[str, dict[str, str]]:  # Added type hint
    """
    Parse and clean a list of FAQ items, extracting relevant information for each card.
    
    Each FAQ item is validated for required fields and cleaned using regex patterns to standardize the text. Only entries with a valid update date are included.
    
    Parameters:
        faqs (list[dict[str, any] | None]): List of FAQ responses, where each item may be None or a list containing FAQ data.
    
    Returns:
        dict[str, dict[str, str]]: A dictionary mapping card codes to their parsed FAQ entries, each containing the code, cleaned text, and update date.
    """
    rulings: dict[str, dict[str, str]] = {}
    for faq_item in tqdm.tqdm(
        faqs, desc="Parsing faqs"
    ):  # Renamed faq to faq_item to avoid confusion
        if not faq_item:  # faq_item can be None if fetch_faq failed
            continue

        # Ensure faq_item is a list and has content, as per original logic for faq[0]
        if not isinstance(faq_item, list) or not faq_item:
            print(f"Unexpected FAQ item format: {faq_item}")
            continue
        faq_content = faq_item[0]

        if (
            not isinstance(faq_content, dict)
            or "html" not in faq_content
            or "code" not in faq_content
            or "updated" not in faq_content
        ):
            print(f"Skipping FAQ item with missing keys: {faq_content}")
            continue

        text = faq_content["html"]
        text = re.sub(constants.SPAN_RULE_PATTERN, r"[\1]", text)
        text = re.sub(constants.NEWLINE_RULE_PATTERN, "\n", text)
        text = re.sub(constants.CARD_LINK_RULE_PATTERN, "/card/", text)
        text = re.sub(constants.RULES_LINK_RULE_PATTERN, "/rules#", text)
        text = re.sub(constants.PARAGRAPH_RULE_PATTERN, "", text)
        text = re.sub(constants.CLOSE_PARAGRAPH_RULE_PATTERN, "", text)

        updated_date = faq_content.get("updated", {}).get("date")
        if not updated_date:
            print(f"Skipping FAQ for card {faq_content['code']} due to missing update date.")
            continue

        entry = {"code": faq_content["code"], "text": text, "updated": updated_date}
        rulings[faq_content["code"]] = entry
    return rulings


async def main() -> None:
    """
    Asynchronously fetches all ArkhamDB card FAQs, parses and cleans the data, and saves the results as a formatted JSON file.
    
    This function retrieves the full set of cards, concurrently fetches their FAQ entries, processes and validates the FAQ data, and writes the cleaned output to the path specified in the constants module. Progress bars are displayed during fetching and parsing for user feedback.
    """
    cards = fetch_cards()
    # cards = cards[:100] # For testing
    # tqdm_async = tqdm_asyncio() # tqdm_asyncio() is not a class to instantiate directly

    all_faq_responses: list[dict[str, any] | None] = []
    async with aiohttp.ClientSession(
        connector=aiohttp.TCPConnector(limit=5, limit_per_host=100)
    ) as session:
        tasks = [
            fetch_faq(session, card) for card in cards if card
        ]  # Added if card to ensure card is not None
        # Wrap tasks with tqdm for progress bar
        all_faq_responses = await tqdm_asyncio.gather(*tasks, desc="Fetching FAQs")

    # Filter out None responses before parsing
    valid_faqs = [faq for faq in all_faq_responses if faq is not None]
    parsed_faq_data = parse_faqs(valid_faqs)

    output_file_path = constants.FAQS_FILE_PATH
    output_file_path.parent.mkdir(parents=True, exist_ok=True)  # Ensure directory exists

    with output_file_path.open("w", encoding="utf-8") as f:
        json.dump(parsed_faq_data, f, indent=2, ensure_ascii=False)
    print(f"Successfully scraped and saved {len(parsed_faq_data)} FAQs to {output_file_path}")


if __name__ == "__main__":
    asyncio.run(main())
