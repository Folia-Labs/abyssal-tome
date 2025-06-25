import datetime
import json
import logging
import uuid
from enum import Enum, auto  # Added StrEnum
from pathlib import Path
from pprint import pp

import bs4
import markdown_it as md_it
import markdownify
from bs4 import BeautifulSoup

# from typing import List, Optional # Replaced by built-in types or new syntax
from pydantic import BaseModel, Field

from symbol import postProcess, tokenize

logging.basicConfig(level=logging.INFO)

# Constants moved to constants.py, except for TEXT_TO_RULING_TYPE
# which are tightly coupled with this script's local RulingType enum.
from abyssal_tome import constants # Updated import path

# TAG_TO_LETTER moved to constants.py
# TAG_TO_LETTER = {
#     "willpower": "p",
#     "agility": "a",
#     "combat": "c",
    "intellect": "b",
    "skull": "k",
    "cultist": "l",
    "tablet": "q",
    "elderthing": "n",
    "autofail": "m",
    "eldersign": "o",
    "bless": "v",
    "curse": "w",
    "frost": "x",
    "reaction": "!",
    "unique": "s",
    "mystic": "g",
    "guardian": "f",
    "seeker": "h",
    "rogue": "d",
    "survivor": "e",
    "free": "j",
    "action": "i",
}


class RulingType(Enum):
    ERRATA = auto()
    ADDENDUM = auto()
    QUESTION_ANSWER = auto()  # Combined type
    CLARIFICATION = auto()
    NOTE = auto()
    # FOLLOWUP_Q can be handled as a new QUESTION_ANSWER
    UPDATE = "UPDATE"
    AS_IF = "AS_IF"
    AUTOMATIC_SUCCESS_FAILURE = "AUTOMATIC_SUCCESS_FAILURE"
    AUTOMATIC_SUCCESS_FAILURE_AUTOMATIC_EVASION = "AUTOMATIC_SUCCESS_FAILURE_AUTOMATIC_EVASION"


class Provenance(BaseModel):
    source_type: str  # E.g., "arkhamdb_faq", "official_faq_pdf", "email_ruling"
    source_name: str | None = None  # E.g., "FAQ v1.7", "Matt Newman Email"
    source_date: str | None = None  # Date of the source document/post
    retrieval_date: str = Field(default_factory=lambda: datetime.datetime.utcnow().isoformat())
    source_url: str | None = None


class Ruling(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source_card_code: str  # Card code this ruling was originally found under
    related_card_codes: list[str] = Field(default_factory=list)
    ruling_type: RulingType  # Now StrEnum
    question: str | None = None  # For QUESTION_ANSWER type
    answer: str | None = None  # For QUESTION_ANSWER type
    text: str | None = None  # For ERRATA, CLARIFICATION, NOTE, etc.
    provenance: Provenance
    original_html_snippet: str | None = (
        None  # The raw HTML snippet for this specific ruling (e.g. <li> content)
    )
    tags: list[str] = Field(default_factory=list)

    # class Config:
    #     arbitrary_types_allowed = True # No longer needed as fields are standard types or Pydantic models


# This mapping uses the RulingType enum defined in this file.
TEXT_TO_RULING_TYPE: dict[str, RulingType] = {
    "errata": RulingType.ERRATA,
    "addendum": RulingType.ADDENDUM,
    "q": RulingType.QUESTION_ANSWER,  # Map Q directly to QUESTION_ANSWER
    # "a": RulingType.ANSWER, # Answer is handled as part of Q
    "clarification": RulingType.CLARIFICATION,
    "note": RulingType.NOTE,
    "follow-up q": RulingType.QUESTION_ANSWER,  # Map Follow-up Q to QUESTION_ANSWER
    "update": RulingType.UPDATE,
    '"as if"': RulingType.AS_IF,
    "automatic success/failure": RulingType.AUTOMATIC_SUCCESS_FAILURE,
    "automatic success/failure &  automatic evasion": RulingType.AUTOMATIC_SUCCESS_FAILURE_AUTOMATIC_EVASION,
}

# RULING_REMOVAL_PATTERNS and RULING_STRIP_PATTERNS moved to constants.py


def load_faqs(faqs_path: Path) -> dict[str, dict[str, str]]:
    # Path validation and loading logic
    if not faqs_path.exists():
        raise FileNotFoundError(f"File {faqs_path} does not exist.")
    if not faqs_path.is_file():
        raise ValueError(f"Path {faqs_path} is not a file.")
    if faqs_path.suffix != ".json":
        raise ValueError(f"File {faqs_path} is not a JSON file.")
    if not faqs_path.stat().st_size > 0:  # Check if file has content
        raise ValueError(f"File {faqs_path} is empty.")

    with faqs_path.open("r", encoding="utf-8") as file:  # Specify encoding
        return json.load(file)


def convert_html_to_markdown(faq_data: dict[str, dict[str, str]]) -> dict[str, str]:
    return {
        card_code: markdownify.markdownify(card_data["text"])
        for card_code, card_data in faq_data.items()
    }


def convert_json_to_html(faq_data: dict[str, dict[str, str]]) -> dict[str, BeautifulSoup]:
    return {
        card_code: BeautifulSoup(card_data["text"], features="html.parser")
        for card_code, card_data in faq_data.items()
    }


def print_token_stream(tokens: List[md_it.token.Token], nest_level: int = 0) -> None:
    for token in tokens:
        for i in range(nest_level):
            print(f"{' ' * 2 * i}Ã¢ÂÂ¾Ã¢ÂÂ¾Ã¢ÂÂ¾|")
        if not token.children:
            tok = token.as_dict(
                children=True, filter=lambda k, v: k in ("type", "tag", "markup", "content")
            )
            print(
                f"{' ' * 4 * nest_level}{tok['type']=} {tok['tag']=} {tok['markup']=} {tok.get('info')=}\n"
            )
            if tok["content"]:
                print(" " * 4 * nest_level, end="")
                pp(tok["content"])
        else:
            childless = token.as_dict(
                children=True, filter=lambda k, v: k in ("type", "tag", "markup", "content")
            )
            if "children" in childless:
                childless.pop("children")
            print(
                f"Parent Token:\n{' ' * 4 * nest_level}{childless['type']=} {childless['tag']=} {childless['markup']=} {childless.get('info')=}\n"
            )
            if childless["content"]:
                print(" " * 4 * nest_level, end="")
                pp(childless["content"])
            print_token_stream(token.children, nest_level + 1)


def process_markdown_faq_data(markdown_faq_data: dict[str, str]) -> None:
    md = md_it.MarkdownIt("gfm-like", {"typographer": True})
    md.enable(["replacements", "smartquotes"])
    md.inline.ruler.push("symbol", tokenize)
    md.inline.ruler2.push("symbol", postProcess)

    for card_code, rulings_text in markdown_faq_data.items():
        tokens = md.parse(rulings_text)
        print(f"Tokens for {card_code}:\n")
        print_token_stream(tokens)
        print(f"\n{'=' * 80}\n\n")


# Regex patterns are now in constants.py (constants.FAQ_VERSION_PATTERN, constants.CARD_LINK_PATTERN)


def extract_faq_source_name(text_content: str) -> str | None:
    match = constants.FAQ_VERSION_PATTERN.search(text_content)
    if match:
        return f"{match.group(1)} v.{match.group(2)}, {match.group(3)}"
    return None


def extract_related_card_codes(html_content: str, current_card_code: str) -> list[str]:
    found_codes = set(constants.CARD_LINK_PATTERN.findall(html_content))
    # Remove the current card's code if it's found, as it's the source_card_code
    return sorted(code for code in found_codes if code != current_card_code)


def process_ruling_html(
    source_card_code: str, ruling_soup: BeautifulSoup, card_updated_at: str | None
) -> list[Ruling]:
    """
    Processes a BeautifulSoup object representing a single ruling item (e.g., content of an <li>)
    and extracts structured Ruling objects.
    """
    rulings_for_item: list[Ruling] = []
    current_question_html_str: str | None = None  # Store HTML string of the question part

    original_snippet_html = ruling_soup.decode_contents().strip()

    # Basic Provenance for ArkhamDB
    base_provenance = Provenance(
        source_type="arkhamdb_faq",
        source_url=f"https://arkhamdb.com/card/{source_card_code}#faq",  # Link to card's FAQ section
        source_date=card_updated_at,  # This is the 'updated_at' for the whole card's FAQ entry on ArkhamDB
        source_name=extract_faq_source_name(
            original_snippet_html
        ),  # Try to get specific FAQ version
    )

    # Iterate over <strong> tags, which usually denote the type of ruling (Q, A, Errata, etc.)
    # We use recursive=True here as strong tags can be nested in other tags within the li
    strong_tags = ruling_soup.find_all("strong")

    if not strong_tags:  # If no strong tags, treat as a single clarification block
        plain_text_content = ruling_soup.get_text(separator=" ", strip=True)
        if plain_text_content:
            rulings_for_item.append(
                Ruling(
                    source_card_code=source_card_code,
                    ruling_type=RulingType.CLARIFICATION,
                    text=plain_text_content,
                    provenance=base_provenance.model_copy(deep=True),
                    original_html_snippet=original_snippet_html,
                    related_card_codes=extract_related_card_codes(
                        original_snippet_html, source_card_code
                    ),
                )
            )
        return rulings_for_item

    for strong_tag in strong_tags:
        tag_text = strong_tag.get_text(strip=True).strip(":").lower()

        content_html_parts: list[str] = []
        current_node = strong_tag.next_sibling
        while current_node:
            if (
                isinstance(current_node, bs4.Tag)
                and current_node.name == "strong"
                and current_node in strong_tags
            ):
                break
            content_html_parts.append(str(current_node))
            current_node = current_node.next_sibling

        # Consolidate content after the strong tag, up to the next strong tag or end of parent
        full_content_html_str = "".join(content_html_parts).strip()
        # Also get a plain text version for Q/A/Text fields
        temp_soup_for_text = BeautifulSoup(full_content_html_str, "html.parser")
        full_content_plain_text = temp_soup_for_text.get_text(separator=" ", strip=True)

        # If no content found directly after, check parent (if strong tag is wrapped)
        if not full_content_html_str and strong_tag.parent and strong_tag.parent.name != "body":
            parent_content_parts: list[str] = []
            # Collect siblings of strong_tag within its parent, but only after the strong_tag
            start_collecting = False
            for child_node in strong_tag.parent.children:
                if child_node == strong_tag:
                    start_collecting = True
                    continue
                if not start_collecting:
                    continue
                if (
                    isinstance(child_node, bs4.Tag)
                    and child_node.name == "strong"
                    and child_node in strong_tags
                ):
                    break
                parent_content_parts.append(str(child_node))
            full_content_html_str = "".join(parent_content_parts).strip()
            temp_soup_for_text = BeautifulSoup(full_content_html_str, "html.parser")
            full_content_plain_text = temp_soup_for_text.get_text(separator=" ", strip=True)

        ruling_type_key = tag_text
        if tag_text.startswith("follow-up q"):
            ruling_type_key = "follow-up q"

        if ruling_type_key in TEXT_TO_RULING_TYPE:
            ruling_type_enum = TEXT_TO_RULING_TYPE[ruling_type_key]
            current_provenance = base_provenance.model_copy(deep=True)
            # Update source_name if a more specific one is found in this segment
            specific_source_name = extract_faq_source_name(full_content_html_str)
            if specific_source_name:
                current_provenance.source_name = specific_source_name

            related_codes = extract_related_card_codes(original_snippet_html, source_card_code)

            if ruling_type_enum == RulingType.QUESTION_ANSWER:
                current_question_html_str = full_content_plain_text  # Store plain text
            elif tag_text == "a" and current_question_html_str is not None:
                rulings_for_item.append(
                    Ruling(
                        source_card_code=source_card_code,
                        ruling_type=RulingType.QUESTION_ANSWER,
                        question=current_question_html_str,
                        answer=full_content_plain_text,
                        provenance=current_provenance,
                        original_html_snippet=original_snippet_html,  # Snippet is for the whole Q&A block
                        related_card_codes=related_codes,
                    )
                )
                current_question_html_str = None
            elif ruling_type_enum != RulingType.QUESTION_ANSWER:
                if current_question_html_str:
                    rulings_for_item.append(
                        Ruling(
                            source_card_code=source_card_code,
                            ruling_type=RulingType.QUESTION_ANSWER,
                            question=current_question_html_str,
                            answer=full_content_plain_text,
                            provenance=current_provenance,
                            original_html_snippet=original_snippet_html,
                            related_card_codes=related_codes,
                        )
                    )
                    current_question_html_str = None
                else:
                    rulings_for_item.append(
                        Ruling(
                            source_card_code=source_card_code,
                            ruling_type=ruling_type_enum,
                            text=full_content_plain_text,
                            provenance=current_provenance,
                            original_html_snippet=original_snippet_html,
                            related_card_codes=related_codes,
                        )
                    )
        elif current_question_html_str:
            rulings_for_item.append(
                Ruling(
                    source_card_code=source_card_code,
                    ruling_type=RulingType.QUESTION_ANSWER,
                    question=current_question_html_str,
                    answer=full_content_plain_text,
                    provenance=base_provenance.model_copy(deep=True),  # Use base for this part
                    original_html_snippet=original_snippet_html,
                    related_card_codes=extract_related_card_codes(
                        original_snippet_html, source_card_code
                    ),
                )
            )
            current_question_html_str = None

    # If after processing all strong tags, there's an uncaptured question, it implies it's a Q without a formal A.
    # Or, if no strong tags were processed but there was content (handled by initial check).
    # This logic might need to be more robust if Qs can exist without any A.

    return rulings_for_item


def process_html_faq_data(raw_faq_json: dict[str, dict]) -> list[Ruling]:
    """
    raw_faq_json is the direct output from load_faqs:
    { card_code: {"text": "<html_string>", "updated_at": "isodate", ...}, ... }
    """
    all_rulings: list[Ruling] = []

    html_content_map = convert_json_to_html(raw_faq_json)  # card_code -> BeautifulSoup

    for card_code, card_level_soup in html_content_map.items():
        card_metadata = raw_faq_json.get(card_code, {})
        card_updated_at: str | None = card_metadata.get("updated_at")  # Get card's last update time

        list_items = card_level_soup.find_all("li")

        if list_items:
            for _item_idx, li_soup in enumerate(
                list_items
            ):  # Consider using _ for item_idx if not used
                rulings_from_li = process_ruling_html(card_code, li_soup, card_updated_at)
                all_rulings.extend(rulings_from_li)
        else:
            rulings_from_block = process_ruling_html(card_code, card_level_soup, card_updated_at)
            all_rulings.extend(rulings_from_block)

    return all_rulings


def main() -> None:
    output_path = constants.PROCESSED_RULINGS_V2_PATH

    try:
        # faq_data now holds the full JSON structure from faqs.json
        faq_data_full = load_faqs(constants.FAQS_FILE_PATH)
    except (FileNotFoundError, ValueError) as e:
        logging.error(f"Error loading faqs: {e}, aborting.")
        return
    else:
        logging.info("Successfully loaded faqs.")

    all_processed_rulings = process_html_faq_data(faq_data_full)

    rulings_as_dicts = [
        ruling.model_dump(mode="json", exclude_none=True) for ruling in all_processed_rulings
    ]

    try:
        with output_path.open("w", encoding="utf-8") as f:
            json.dump(rulings_as_dicts, f, indent=2, ensure_ascii=False)
        logging.info(f"Successfully processed rulings and saved to {output_path}")
    except OSError as e:
        logging.error(f"Error writing processed rulings to {output_path}: {e}")

    # markdown_faq_data = convert_html_to_markdown(faq_data)

    # process_markdown_faq_data(markdown_faq_data)


if __name__ == "__main__":
    main()
