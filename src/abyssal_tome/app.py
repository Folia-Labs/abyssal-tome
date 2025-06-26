import asyncio
import json
import logging
import os
import sys
from base64 import b64encode, urlsafe_b64decode, urlsafe_b64encode
from copy import deepcopy
from enum import StrEnum, unique
from pathlib import Path

import clipman
import flet as ft
import flet_fastapi
import regex as reg
import requests
from gql import Client, gql
from gql.transport.aiohttp import AIOHTTPTransport as GQL_Transport
from starlette.middleware.cors import CORSMiddleware
from tqdm.auto import tqdm
from whoosh.fields import ID, TEXT, Schema
from whoosh.index import create_in, open_dir
from whoosh.writing import AsyncWriter

from .utils import debounce  # Corrected relative import
from . import constants  # Import constants from the package

logging.basicConfig(level=logging.WARNING, stream=sys.stdout)

# DEFAULT_FLET_PATH and DEFAULT_FLET_PORT are now in constants.py

clipman.init()

schema = Schema(
    card_name=ID(stored=True),
    ruling_text=TEXT,
    card_code=ID(stored=True),
    ruling_type=TEXT,
    ruling_question=TEXT,
    ruling_answer=TEXT,
)
if not Path("indexdir").exists():
    Path("indexdir").mkdir()
ix = create_in("indexdir", schema)

@unique
class EntryType(StrEnum):
    UNKNOWN = "unknown"
    ERRATUM = "erratum"
    QUESTION_ANSWER = "question/answer"
    CLARIFICATION = "clarification"

@unique
class QAType(StrEnum):
    QUESTION = "question"
    ANSWER = "answer"

# Use TAG_TO_LETTER from constants to ensure consistency
TAG_TO_LETTER = constants.TAG_TO_LETTER

LINK_PATTERN = reg.compile(r"\[(?P<link_text>[^\[\]]+)\](?=\([^\)]+\))\((?P<link_url>[^\(\)]+)\)")
TAG_PATTERN = reg.compile(
    r"(?P<tag>"
    + r"|".join(reg.escape(f"[{tag}]", special_only=True) for tag in constants.TAG_TO_LETTER)
    + ")"
)
BOLD_ITALIC_PATTERN = reg.compile(r"\*\*\*(?P<bold_italic>.*?)\*\*\*")
BOLD_PATTERN = reg.compile(r"\*\*(?P<bolded>.*?)\*\*")
ITALIC_PATTERN = reg.compile(r"\*(?P<italics>.*?)\*")
ALL_PATTERN = reg.compile(
    "|".join(
        pat.pattern
        for pat in (LINK_PATTERN, TAG_PATTERN, BOLD_ITALIC_PATTERN, BOLD_PATTERN, ITALIC_PATTERN)
    )
)

transport = GQL_Transport(url="https://gapi.arkhamcards.com/v1/graphql")
gql_client = Client(transport=transport, fetch_schema_from_transport=True)

def load_json_data() -> dict:
    # This function should load from the new processed_rulings_v3_ai_enriched.json
    # or whatever the final data source for the app will be.
    # For now, keeping it as processed_data.json to avoid breaking existing logic
    # until model.py loading is fully integrated.
    """
    Load and return card rulings data from the local JSON file.
    
    Returns:
        dict: Parsed JSON data containing card rulings and related information.
    """
    logging.info("Loading JSON data from file.")
    with Path("assets/processed_data.json").open(encoding="utf-8") as file:
        data = json.load(file)
    logging.info("JSON data loaded successfully.")
    return data

def highlight_text(span: ft.TextSpan, search_term: str) -> list[ft.TextSpan]:
    """
    Highlight occurrences of a search term within a TextSpan, returning new spans with background color applied to matches.
    
    If the span represents a tag icon matching the search term, highlights the entire icon. Otherwise, splits the span into segments, applying a highlight style to each substring that matches the search term. Returns the resulting list of TextSpans, or the original span if no matches are found.
    
    Parameters:
    	span (ft.TextSpan): The text span to search and highlight within.
    	search_term (str): The term to highlight.
    
    Returns:
    	list[ft.TextSpan]: A list of text spans with highlighted matches.
    """
    term_pattern = reg.escape(search_term, special_only=True, literal_spaces=True)
    for tag_name_in_dict, icon_char in TAG_TO_LETTER.items(): # Corrected variable name
        if (
            search_term.lower() in tag_name_in_dict # Check against keys like "willpower"
            and span.style
            and span.style.font_family == "Arkham Icons"
            and span.text == icon_char
        ):
            span.style.bgcolor = ft.colors.with_opacity(0.5, ft.colors.TERTIARY)
            return [span]

    compiled_term_pattern = reg.compile(term_pattern, reg.IGNORECASE) # Compile pattern once
    span_text = span.text
    spans = []
    span_style = span.style if span.style else ft.TextStyle() # Ensure span_style is not None
    highlight_style = deepcopy(span_style)
    highlight_style.bgcolor = ft.colors.with_opacity(0.5, ft.colors.TERTIARY)

    if not span_text:
        return []

    remaining_text = span_text
    while match := compiled_term_pattern.search(remaining_text): # Use compiled pattern
        start, end = match.span()
        if start > 0:
            pre_span = deepcopy(span)
            pre_span.text = remaining_text[:start]
            spans.append(pre_span)

        mid_span = deepcopy(span)
        mid_span.text = remaining_text[start:end]
        mid_span.style = highlight_style
        spans.append(mid_span)

        remaining_text = remaining_text[end:]
        if not remaining_text:
            break

    if remaining_text:
        end_span = deepcopy(span)
        end_span.text = remaining_text
        spans.append(end_span)

    return spans if spans else [span] # Return original span if no matches, to keep content
async def highlight_spans(text_spans: list[ft.TextSpan], search_term: str) -> list[ft.TextSpan]:
    """
    Highlights all occurrences of a search term within a list of TextSpan objects.
    
    Parameters:
        text_spans (list[ft.TextSpan]): The list of text spans to process.
        search_term (str): The term to highlight within the text spans.
    
    Returns:
        list[ft.TextSpan]: A new list of TextSpan objects with matching substrings highlighted.
    """
    highlighted_spans = []
    for span_item in text_spans: # Renamed span to span_item
        highlighted_spans.extend(await highlight_text(span_item, search_term))
    return highlighted_spans

def append_span(spans_list: list[ft.TextSpan], text_content: str, style: ft.TextStyle | None = None, on_click_handler=None) -> None: # Renamed variables
    """
    Appends a new TextSpan with the specified text, style, and optional click handler to the provided list if the text is not empty.
    
    Parameters:
        spans_list (list[ft.TextSpan]): The list to which the new TextSpan will be added.
        text_content (str): The text content for the new TextSpan.
        style (ft.TextStyle, optional): The style to apply to the TextSpan. Defaults to an empty TextStyle if not provided.
        on_click_handler (callable, optional): An optional click event handler for the TextSpan.
    """
    if text_content:
        spans_list.append(ft.TextSpan(text=text_content, style=style or ft.TextStyle(), on_click=on_click_handler))

async def replace_special_tags(page: ft.Page, text_input: str) -> list[ft.TextSpan]:
    """
     """
     Parses input text for special tags, markdown styles, and links, converting them into styled TextSpan objects for display.
async def on_card_click(event: ft.ControlEvent, page: ft.Page, card_id: str) -> None:
    """
    Displays a modal dialog with the card image when a card is clicked.
    
    Opens an alert dialog containing the card's image, retrieved asynchronously by card ID, and provides a close button to dismiss the dialog.
    """
    logging.info(f"Card clicked with ID: {card_id}")
    image_url = await retrieve_image_url(card_id)
    dialog_ref = ft.Ref[ft.AlertDialog]() # Create a ref for the dialog

    async def close_dialog(_event=None) -> None: # Add _event param
        """
        Closes the currently open dialog and updates the page asynchronously.
        """
        if dialog_ref.current:
            dialog_ref.current.open = False
        await page.update_async() # Update page to reflect dialog closure

    image = await retrieve_image_binary(image_url)
    image_card = ft.Image(src_base64=image, expand=True)
    close_button = ft.IconButton(icon=ft.icons.CLOSE, on_click=close_dialog)
    dialog_content = ft.Card(content=image_card, expand=True) # Use content property

    dialog = ft.AlertDialog(
        ref=dialog_ref,
        content=dialog_content,
        actions=[close_button],
        actions_alignment=ft.MainAxisAlignment.START,
        modal=True,
        on_dismiss=lambda e: print("Dialog dismissed!"),
        shape=ft.RoundedRectangleBorder(radius=ft.border_radius.all(0)),
        content_padding=ft.padding.all(0),
    )
    page.dialog = dialog
    dialog.open = True
    await page.update_async()

async def retrieve_image_binary(image_url: str) -> str:
    """
    Fetch an image from the specified URL and return its content as a base64-encoded ASCII string.
    
    Parameters:
        image_url (str): The URL of the image to retrieve.
    
    Returns:
        str: Base64-encoded ASCII string of the image content, or an empty string if retrieval fails.
    """
    import aiohttp

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(image_url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status != 200:
                    logging.error(f"Image URL: {image_url} returned status code: {response.status}")
                    return ""
                logging.info(f"Image URL: {image_url} returned status code: {response.status}")
                image_data = await response.read()
                return b64encode(image_data).decode("ascii")
        except Exception as e:
            logging.error(f"Failed to retrieve image from {image_url}: {e}")
            return ""
async def retrieve_image_url(card_id: str) -> str | None: # Return None if not found
    """
    Fetches the image URL for a card using its card ID via a GraphQL query.
    
    Parameters:
    	card_id (str): The unique identifier of the card.
    
    Returns:
    	str | None: The image URL as a string if found, otherwise None.
    """
    gql_query = gql(f"""query getCardImageURL {{ all_card(where: {{code: {{_eq: "{card_id}"}}}}) {{ imageurl }} }}""")
    gql_result = await gql_client.execute_async(gql_query)
    if gql_result and "all_card" in gql_result and gql_result["all_card"] and "imageurl" in gql_result["all_card"][0]:
        image_url = gql_result["all_card"][0]["imageurl"]
        if image_url:
            return str(image_url) # Ensure it's a string
    logging.error(f"No image URL found for card_id: {card_id}")
    return None

async def retrieve_card_text(card_id: str) -> dict | None: # Return None if not found
    """
    Fetches detailed text information for a card by its ID using a GraphQL query.
    
    Parameters:
    	card_id (str): The unique identifier of the card.
    
    Returns:
    	dict | None: A dictionary containing card text fields if found, otherwise None.
    """
    gql_query = gql(f"""query getCardText {{ all_card_text(where: {{id: {{_eq: "{card_id}"}}}}) {{ back_flavor back_name back_text back_traits customization_change customization_text encounter_name taboo_original_back_text taboo_original_text taboo_text_change }} }}""")
    gql_result = await gql_client.execute_async(gql_query)
    if gql_result and "all_card_text" in gql_result and gql_result["all_card_text"]:
        return gql_result["all_card_text"][0]
    logging.error(f"No card text results found for card_id: {card_id}")
    return None

async def copy_ruling_to_clipboard(event: ft.ControlEvent, ruling_text_content: str, button_to_style: ft.IconButton) -> None: # Renamed params
    """
    Copies the specified ruling text to the clipboard and briefly highlights the associated button to indicate success.
    
    Parameters:
        ruling_text_content (str): The text of the ruling to be copied to the clipboard.
        button_to_style (ft.IconButton): The button to visually highlight after copying.
    """
    logging.info("Copying ruling to clipboard.")
    clipman.copy(ruling_text_content)
    if button_to_style: # Check if button exists
        button_to_style.style.shadow = ft.BoxShadow(
            spread_radius=-1, blur_radius=10, color=ft.colors.BLACK,
            offset=ft.Offset(2, 2), blur_style=ft.ShadowBlurStyle.NORMAL,
        )
        await button_to_style.update_async()
        await asyncio.sleep(0.3)
        button_to_style.style.shadow = None
        await button_to_style.update_async()

async def go_to_card_page(event: ft.ControlEvent, page: ft.Page, card_code: str, card_name: str) -> None:
    """
    Navigates asynchronously to the detailed view of a card using its code and name.
    
    The card name is base64-encoded for safe URL inclusion. After navigation, the page is updated to reflect the new route.
    """
    await page.go_async(f"/card/{urlsafe_b64encode(card_name.encode('utf-8')).decode('ascii')}/{card_code}") # Ensure utf-8
    await page.update_async()

class SearchController:
    def __init__(self, page: ft.Page, data: dict[str, list[dict]]) -> None:
        """
        Initialize the SearchController with the Flet page and card rulings data.
        
        Parameters:
            page (ft.Page): The Flet page instance for UI updates.
            data (dict[str, list[dict]]): Dictionary mapping card names to lists of ruling entries.
        """
        logging.info("Initializing SearchController.") # Corrected class name
        self.page = page
        self.page_content: ft.Column = page.views[0].controls[1] # This might be fragile
        self.data = data

    async def create_text_spans(self, ruling_type: EntryType, search_term: str | None, ruling_text_content: str = "", question_or_answer: QAType | None = None) -> list[ft.TextSpan]: # Added None to search_term
        """
        Generate a list of styled TextSpan objects for a ruling, optionally highlighting a search term.
        
        Parameters:
            ruling_type (EntryType): The type of ruling entry.
            search_term (str | None): The term to highlight within the ruling text, if provided.
            ruling_text_content (str): The main text content of the ruling.
            question_or_answer (QAType | None): Specifies if the entry is a question or answer for QUESTION_ANSWER types.
        
        Returns:
            list[ft.TextSpan]: A list of TextSpan objects representing the formatted and optionally highlighted ruling text.
        """
        if not ruling_text_content:
            return []
        ruling_type_name = ruling_type.title()
        if ruling_type == EntryType.QUESTION_ANSWER:
            ruling_type_name = question_or_answer.title() if question_or_answer else "Entry"

        text_spans = [ft.TextSpan(text=f"{ruling_type_name}: ", style=ft.TextStyle(weight=ft.FontWeight.BOLD))]
        ruling_text_control_spans = await replace_special_tags(self.page, ruling_text_content)
        if search_term: # Only highlight if search_term is provided
            ruling_text_control_spans = await highlight_spans(ruling_text_control_spans, search_term)
        text_spans.extend(ruling_text_control_spans)
        return text_spans

    async def update_search_view(self, search_term: str) -> None:

        """
        Update the search results view to display card rulings matching the provided search term.
        
        Filters all card rulings for matches with the search term (case-insensitive), groups results by card, and displays each matching ruling with a copy-to-clipboard button and highlighted search terms. If no results are found, displays a message indicating no matches. Updates the page asynchronously.
        """
        def _create_copy_button_lambda(btn_ruling_text, btn_ruling_question, btn_ruling_answer, btn_instance: ft.IconButton):
            # This inner function is needed because lambdas capture variables by name from the enclosing scope at definition time
            # but we need to pass the button *instance* that the lambda is attached to.
            # However, the button instance isn't fully defined when the lambda is defined.
            # A workaround is to have the button call a method that then knows about the button.
            # For now, we pass the button instance to the copy_ruling_to_clipboard.
            rules_text_content = btn_ruling_text or rf"Q: {btn_ruling_question}\n A: {btn_ruling_answer}"
            return lambda e: asyncio.create_task(copy_ruling_to_clipboard(e, rules_text_content, btn_instance))

        self.page_content.scroll = None # Consider ft.ScrollMode.ADAPTIVE or ft.ScrollMode.AUTO
        self.page_content.controls.clear()

        content_controls = ft.ListView(controls=[], expand=True, spacing=10)
        if not search_term:
            logging.warning("update_search_view called with empty search_term.")
            # Optionally, display all items or a message
            # self.page_content.controls.append(ft.Text("Enter a search term to begin."))
            # await self.page.update_async()
            # return

        for card_name, card_rulings in tqdm(self.data.items(), total=len(self.data), desc="Processing cards"):
            card_added = False
            card_specific_controls = [] # Controls for the current card

            for _i, ruling in enumerate(card_rulings):
                ruling_content = ruling.get("content", {})
                ruling_type_str = ruling.get("type", EntryType.UNKNOWN.value)
                try:
                    ruling_type = EntryType(ruling_type_str)
                except ValueError:
                    ruling_type = EntryType.UNKNOWN

                ruling_text_val = ruling_content.get("text", "") # Renamed to avoid conflict
                ruling_question = ruling_content.get("question", "")
                ruling_answer = ruling_content.get("answer", "")
                card_id = ruling.get("card_code", "")

                current_ruling_text_for_search = f"{ruling_text_val} {ruling_question} {ruling_answer}"
                if search_term.lower() not in current_ruling_text_for_search.lower():
                    continue

                if not card_added:
                    card_added = True
                    card_specific_controls.append(
                        ft.Text(
                            spans=[
                                ft.TextSpan(
                                    card_name, style=ft.TextStyle(decoration=ft.TextDecoration.UNDERLINE),
                                    on_click=lambda e, name=card_name, code=card_id: asyncio.create_task(go_to_card_page(e, self.page, code, name))
                                )
                            ],
                            theme_style=ft.TextThemeStyle.TITLE_MEDIUM, selectable=True
                        )
                    )

                text_spans_for_display = []
                copy_button = ft.IconButton(icon=ft.icons.COPY, icon_size=20, tooltip="Copy ruling")
                # The lambda needs to correctly capture rule_text, question, answer for *this* button
                full_ruling_text_for_copy = ruling_text_val or rf"Q: {ruling_question}\n A: {ruling_answer}"
                copy_button.on_click = lambda e, rt=full_ruling_text_for_copy, btn=copy_button: asyncio.create_task(copy_ruling_to_clipboard(e, rt, btn))

                text_spans_for_display.append(copy_button)


                if ruling_type == EntryType.QUESTION_ANSWER:
                    if ruling_question:
                        text_spans_for_display.extend(await self.create_text_spans(ruling_type, search_term, ruling_question, QAType.QUESTION))
                        text_spans_for_display.append(ft.TextSpan(text="\n"))
                    if ruling_answer:
                        text_spans_for_display.extend(await self.create_text_spans(ruling_type, search_term, ruling_answer, QAType.ANSWER))
                elif ruling_text_val:
                    text_spans_for_display.extend(await self.create_text_spans(ruling_type, search_term, ruling_text_val))
                else: # Fallback for UNKNOWN or empty
                     text_spans_for_display.append(ft.TextSpan("Ruling content appears empty or unknown."))


                card_specific_controls.append(
                    ft.Container(
                        content=ft.Row([ft.Text(spans=text_spans_for_display, selectable=True, expand=True)], scroll=None, expand=True),
                        # padding=ft.padding.symmetric(vertical=5) # Add some padding
                    )
                )

            if card_added:
                content_controls.controls.append(ft.Column(card_specific_controls, spacing=5))
                content_controls.controls.append(ft.Divider(height=10, thickness=2))


        self.page_content.controls.clear()
        self.page_content.controls.append(ft.Text(spans=[ft.TextSpan("Search results for "), ft.TextSpan(f'"{search_term}"')], theme_style=ft.TextThemeStyle.HEADLINE_MEDIUM))

        if not content_controls.controls:
            logging.info(f"No search results found for term: {search_term}")
            content_controls.controls.append(ft.Text("No results found."))

        self.page_content.controls.append(content_controls)
        await self.page.update_async()
        # await self.page_content.update_async() # page.update_async() should cover this

    async def get_rulings_for_card(self, page: ft.Page, card_name: str, card_code: str, image_binary: str | None, card_text_data: dict | None) -> list[ft.Control]: # card_text renamed to card_text_data

        """
        Retrieve and format all rulings for a specific card as UI controls for display in the card detail view.
        
        Parameters:
        	card_name (str): The name of the card whose rulings are to be displayed.
        	card_code (str): The unique code identifying the card.
        	image_binary (str | None): Base64-encoded image data for the card, if available.
        	card_text_data (dict | None): Additional card text details, if available.
        
        Returns:
        	list[ft.Control]: A list of Flet UI controls representing the card's rulings, each with copy-to-clipboard functionality and styled text. If no rulings are found, returns a message indicating this.
        """
        def _create_copy_button_lambda_for_card_view(btn_ruling_text, btn_ruling_question, btn_ruling_answer, btn_instance: ft.IconButton):
            rules_text_content = btn_ruling_text or rf"Q: {btn_ruling_question}\n A: {btn_ruling_answer}"
            return lambda e: asyncio.create_task(copy_ruling_to_clipboard(e, rules_text_content, btn_instance))

        card_rulings_list = self.data.get(card_name, [])
        display_controls = []

        for ruling in card_rulings_list:
            ruling_content = ruling.get("content", {})
            ruling_type_str = ruling.get("type", EntryType.UNKNOWN.value)
            try:
                ruling_type = EntryType(ruling_type_str)
            except ValueError:
                ruling_type = EntryType.UNKNOWN

            ruling_text_val = ruling_content.get("text", "")
            ruling_question = ruling_content.get("question", "")
            ruling_answer = ruling_content.get("answer", "")

            text_spans = []
            copy_button = ft.IconButton(icon=ft.icons.COPY, icon_size=20, tooltip="Copy ruling")
            full_ruling_text_for_copy = ruling_text_val or rf"Q: {ruling_question}\n A: {ruling_answer}"
            copy_button.on_click = lambda e, rt=full_ruling_text_for_copy, btn=copy_button: asyncio.create_task(copy_ruling_to_clipboard(e, rt, btn))
            text_spans.append(copy_button)

            if ruling_type == EntryType.QUESTION_ANSWER:
                if ruling_question:
                    text_spans.extend(await self.create_text_spans(ruling_type, None, ruling_question, QAType.QUESTION))
                    text_spans.append(ft.TextSpan(text="\n"))
                if ruling_answer:
                    text_spans.extend(await self.create_text_spans(ruling_type, None, ruling_answer, QAType.ANSWER))
            elif ruling_text_val:
                 text_spans.extend(await self.create_text_spans(ruling_type, None, ruling_text_val))
            else:
                text_spans.append(ft.TextSpan(f"({ruling_type.title()}) Content missing."))

            display_controls.append(ft.Text(spans=text_spans, selectable=True))
            display_controls.append(ft.Divider(height=5))

        return display_controls if display_controls else [ft.Text("No rulings found for this card in the local data.")]


class SearchInputController:
    def __init__(self, page: ft.Page, data: dict[str, list[dict]]) -> None:
        """
        Initialize the SearchInputController with the given Flet page and card rulings data.
        """
        logging.info("Initializing SearchInputController.") # Corrected class name
        self.data = data
        self.page = page

    @debounce(1.0)
    async def search_input_changed(self, event: ft.ControlEvent) -> None:
        """
        Handles changes to the search input field and updates the search results view with matching rulings.
        
        This method is debounced to limit update frequency during rapid input changes.
        """
        if search_term := event.control.value:
            # Use SearchController, not SearchView
            search_controller = SearchController(self.page, self.data)
            await search_controller.update_search_view(search_term)


async def main_flet_app(page: ft.Page) -> None: # Renamed main to main_flet_app
    """
    Initializes and runs the main Flet application, setting up the UI, search functionality, and navigation for the FAQ card rulings interface.
    
    This function configures the page theme, loads and indexes card ruling data, and constructs the root view with a search input and dynamic content area. It registers asynchronous handlers for route changes and view navigation, enabling transitions between the search results and detailed card views with images and rulings. The application supports both web and desktop environments, integrating with FastAPI for web deployment.
    """
    print("Flet Main function started.")
    page.title = "FAQ This!"
    page.fonts = {"Arkham Icons": "/fonts/arkham-icons.otf"}
    # ... (theme setup remains the same) ...
    page.theme = ft.Theme(
        color_scheme=ft.ColorScheme(
            primary="#ff436915",
            on_primary="#ffffffff",
            primary_container="#ffc2f18d",
            on_primary_container="#ff0f2000",
            secondary="#ff57624a",
            on_secondary="#ffffffff",
            secondary_container="#ffdbe7c8",
            on_secondary_container="#ff151e0b",
            tertiary="#ff386663",
            on_tertiary="#ffffffff",
            tertiary_container="#ffbbece8",
            on_tertiary_container="#ff00201f",
            error="#ffba1a1a",
            error_container="#ffffdad6",
            on_error="#ffffffff",
            on_error_container="#ff410002",
            background="#fffdfcf5",
            on_background="#ff1b1c18",
            surface="#fffdfcf5",
            on_surface="#ff1b1c18",
            surface_variant="#ffe1e4d5",
            on_surface_variant="#ff44483d",
            outline="#ff75796c",
            on_inverse_surface="#fff2f1e9",
            inverse_surface="#ff30312c",
            inverse_primary="#ffa7d474",
            shadow="#ff000000",
            surface_tint="#ff436915",
            outline_variant="#ffc5c8ba",
            scrim="#ff000000",
        )
    )

    page_content_ref = ft.Ref[ft.Column]() # Use Ref
    json_data = load_json_data()

    # Indexing (consider doing this once at startup, not per page load if main_flet_app is called multiple times)
    # For a desktop app, this is fine. For web, this might be inefficient.
    # Use existing ix variable created at module level
    print("Creating/Opening index.")
    with AsyncWriter(ix) as writer:
        for card_name, card_rulings in tqdm(json_data.items(), desc="Indexing cards"):
            for ruling in card_rulings:
                writer.add_document(
                    card_name=card_name,
                    ruling_text=ruling.get("content", {}).get("text", ""),
                    card_code=ruling.get("card_code", ""),
                    ruling_type=ruling.get("type", EntryType.UNKNOWN.value),
                    ruling_question=ruling.get("content", {}).get("question", ""),
                    ruling_answer=ruling.get("content", {}).get("answer", ""),
                )

    search_input_handler = SearchInputController(page, json_data)
    search_input = ft.TextField(
        hint_text="Type to search...",
        on_change=search_input_handler.search_input_changed, # Directly pass the method
        autofocus=True, autocorrect=False, icon=ft.icons.SEARCH, expand=True
    )

    root_view_controls = [
        ft.AppBar(title=ft.Text("FAQ This!"), bgcolor=ft.colors.SURFACE_VARIANT),
        ft.Row([search_input]), # Search input at the top
        ft.Column(ref=page_content_ref, expand=True, scroll=ft.ScrollMode.ADAPTIVE), # Content area
    ]
    # Ensure page_content_ref is assigned if SearchController relies on it being in page.views[0]
    # This structure is a bit different now.
    # The SearchController might need to be adapted to find its target Column if not page.views[0].controls[1]

    page.views.append(ft.View("/", root_view_controls))
    await page.update_async()


    async def route_change(route_event: ft.RouteChangeEvent) -> None:
        """
        Handles route changes to display either the card detail view or the main search view.
        
        When navigating to a card detail route, retrieves the card's image and text, gathers its rulings, and displays them in a new view. When returning to the home route, removes the detail view to show the search interface.
        """
        print(f"Route change: {route_event.route}")
        # page.views.clear() # This would clear the root view with search
        # page.views.append(root_view) # Keep root view

        current_page_content_column = page_content_ref.current # Get the current column to update

        troute = ft.TemplateRoute(route_event.route)
        if troute.match("/card/:card_name_b64/:card_code"): # Use a different param name
            card_code = troute.card_code
            card_name = urlsafe_b64decode(troute.card_name_b64).decode("utf-8") # Use utf-8

            image_url = await retrieve_image_url(card_code)
            image_binary_data = None
            if image_url:
                image_binary_data = await retrieve_image_binary(image_url)

            card_text_content = await retrieve_card_text(card_code) # Renamed card_text

            # Use SearchController, not SearchView
            search_controller = SearchController(page, json_data) # json_data needs to be accessible
            ruling_controls = await search_controller.get_rulings_for_card(page, card_name, card_code, image_binary_data, card_text_content)

            # Create new view for card details
            card_detail_view_content = [
                ft.AppBar(title=ft.Text(f"{card_name} ({card_code})"), bgcolor=ft.colors.SURFACE_VARIANT),
                ft.Row([
                        ft.Column(
                            [ft.Image(src_base64=image_binary_data) if image_binary_data else ft.Text("No Image")],
                            expand=2, alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        ft.Column(
                            [ft.Text("Rulings", theme_style=ft.TextThemeStyle.HEADLINE_SMALL)] + ruling_controls,
                            expand=6, scroll=ft.ScrollMode.ADAPTIVE,
                        ),
                    ],
                    expand=True, vertical_alignment=ft.CrossAxisAlignment.START
                ),
            ]

            # If there's more than one view, it means we are in a detail view, replace the last one.
            # Otherwise, append. This logic might need refinement for proper back navigation.
            new_view = ft.View(route_event.route, card_detail_view_content)
            if len(page.views) > 1 and page.views[-1].route != "/":
                 page.views[-1] = new_view # Replace current detail view
            else:
                 page.views.append(new_view)

        elif route_event.route == "/": # Navigating back to home
            if len(page.views) > 1: # If we were in a detail view
                page.views.pop() # Remove the detail view

        await page.update_async()

    async def view_pop(view_event: ft.ViewPopEvent) -> None: # Corrected param name
        """
        Handles the event when a view is popped from the navigation stack, navigating to the previous view's route.
        """
        page.views.pop()
        top_view = page.views[-1]
        await page.go_async(top_view.route)

    page.on_route_change = route_change # No need for create_task here
    page.on_view_pop = view_pop # No need for create_task here

    print("Navigating to initial route.")
    await page.go_async(page.route)


logging.info("Starting app.")
print("Starting app")
flet_path = os.getenv("FLET_PATH", DEFAULT_FLET_PATH)
flet_port = int(os.getenv("FLET_PORT", DEFAULT_FLET_PORT))
# Pass main_flet_app to flet_fastapi.app
app = flet_fastapi.app(main_flet_app, assets_dir=str(Path(__file__).parent / "assets"), web_renderer=ft.WebRenderer.HTML)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)

if __name__ == "__main__":
    # This part is for running Flet as a standalone desktop app, not via FastAPI
    # For FastAPI, `uvicorn main:app --reload` would be used from the terminal.
    # To run as desktop (if desired, and flet_fastapi is not the primary mode):
    # ft.app(target=main_flet_app, assets_dir="assets")
    print("To run with FastAPI: uvicorn main:app --reload --port", flet_port)
    print("This __main__ block is for information or direct Flet desktop app mode (currently commented out).")
    # For direct Flet execution (without FastAPI):
    # ft.app(target=main_flet_app, assets_dir=str(Path(__file__).parent / "assets"), view=ft.WEB_BROWSER, port=flet_port)

