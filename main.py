from enum import StrEnum, unique

import flet as ft
import asyncio
import contextlib
import json
import regex as re
from functools import singledispatch
from pathlib import Path
from gql import Client, gql
from gql.transport.aiohttp import AIOHTTPTransport as GQL_Transport

# from gql.utilities.build_client_schema import GraphQLSchema

@unique
class EntryType(StrEnum):
    ERRATUM = "erratum"
    QUESTION_ANSWER = "question/answer"
    CLARIFICATION = "clarification"

TAG_TO_IMAGE = {
    "[willpower]": "p",
    "[agility]": "a",
    "[combat]": "c",
    "[intellect]": "b",
    "[skull]": "k",
    "[cultist]": "l",
    "[tablet]": "q",
    "[elderthing]": "n",
    "[autofail]": "m",
    "[eldersign]": "o",
    "[bless]": "v",
    "[curse]": "w",
    "[frost]": "x",
    "[reaction]": "!",
    "[unique]": "s",
    "[mystic]": "g",
    "[guardian]": "f",
    "[seeker]": "h",
    "[rogue]": "d",
    "[survivor]": "e",
    "[free]": "j",
    "[activate]": "i",
}

LINK_PATTERN = re.compile(r"\[(.+?)\]\((.+?)\)")

transport = GQL_Transport(url="https://gapi.arkhamcards.com/v1/graphql")
gql_client = Client(transport=transport, fetch_schema_from_transport=True)


# Function to highlight the search term in text
# It finds the search term in the text and then creates three ft.TextSpan objects:

def debounce(wait):
    def decorator(fn):
        @functools.wraps(fn)
        async def debounced(*args, **kwargs):
            debounced._task = getattr(debounced, '_task', None)
            if debounced._task is not None:
                debounced._task.cancel()
            debounced._task = asyncio.ensure_future(fn(*args, **kwargs))
            with contextlib.suppress(asyncio.CancelledError):
                await asyncio.sleep(wait)
                await debounced._task

        return debounced

    return decorator


def load_json_data() -> dict:
    with open('assets/processed_data.json', 'r', encoding='utf-8') as file:
        data = json.load(file)
    return data


# Function to highlight the search term in text
# It finds the search term in the text and then creates three ft.TextSpan objects:
# 1. The text before the search term
# 2. The search term itself
# 3. The text after the search term
# The search term is highlighted by setting its color to yellow
@singledispatch
def highlight(text, term: str) -> list:
    raise ValueError("Unsupported text type for highlighting")

@highlight.register
def _(text: str, term: str) -> list:
    return _highlight_string(text, term)

@highlight.register
def _(text: ft.TextSpan, term: str) -> list:
    return _highlight_textspan(text, term)

@highlight.register
def _(text: list, term: str) -> list:
    return _highlight_list(text, term)

def _highlight_string(text, term) -> list:
    spans = []
    lower_text = text.lower()
    lower_term = term.lower()
    start = 0
    while (index := lower_text.find(lower_term, start)) != -1:
        if index > start:
            spans.append(ft.TextSpan(text=text[start:index]))
        spans.append(ft.TextSpan(
            text=text[index:index+len(term)],
            style=ft.TextStyle(weight=ft.FontWeight.BOLD, bgcolor=ft.colors.BLUE_50)
        ))
        start = index + len(term)
    if start < len(text):
        spans.append(ft.TextSpan(text=text[start:]))
    return spans

def _highlight_textspan(textspan, term) -> list:
    if textspan.spans:
        return [ft.TextSpan(spans=_highlight_list(textspan.spans, term), style=textspan.style)]
    else:
        return _highlight_string(textspan.text, term)

def _highlight_list(spans, term) -> list:
    highlighted_spans = []
    for span in spans:
        highlighted_spans.extend(highlight(span, term))
    return highlighted_spans


LINK_PATTERN = re.compile(r"\[(.+?)\]\((.+?)\)")

import re
import flet as ft
from flet import Alignment

TAG_PATTERN = re.compile('|'.join(re.escape(tag) for tag in TAG_TO_IMAGE))


def replace_special_tags(page: ft.Page, text: str) -> list[ft.TextSpan]:
    spans = []
    remaining_text = text

    while match := LINK_PATTERN.search(remaining_text) or TAG_PATTERN.search(remaining_text):
        start, end = match.span()
        if start > 0:
            spans.append(ft.TextSpan(text=remaining_text[:start]))
        if match.re.pattern == LINK_PATTERN.pattern:
            link_text, link_url = match.groups()
            card_id = link_url.split("/")[-1]
            spans.append(ft.TextSpan(text=link_text, style=ft.TextStyle(decoration=ft.TextDecoration.UNDERLINE,
                                                                        color=ft.colors.BLUE_ACCENT_400),
                                     on_click=lambda event: on_card_click(event, page, card_id)))
        else:
            tag = match.group()
            image_name = TAG_TO_IMAGE[tag]
            spans.append(ft.TextSpan(text=image_name, style=ft.TextStyle(size=20, font_family="Arkham Icons")))
        remaining_text = remaining_text[end:]

    if remaining_text:
        spans.append(ft.TextSpan(text=remaining_text))

    return spans


def on_card_click(event, page: ft.Page, card_id):
    gql_query = gql(
        f"""
        query getCardImageURL {{
            all_card (where: {{code: {{_eq: "{card_id}"}}}}) {{
                imageurl
            }}
        }}
        """
    )
    gql_result = gql_client.execute(gql_query)
    # image_url = gql_result['data']['all_card'][0]['imageurl']
    print(gql_result)
    image_url = gql_result['all_card'][0]['imageurl']

    def close_dialog():
        dialog.open = False  # Close the Dialog
        page.close_dialog()
        asyncio.run(page.close_dialog_async())
        page.dialog = None
        # dialog.visible = False  # Hide the Dialog

        page.update()

    image_card = ft.Image(src=image_url)
    # Close button to dismiss the Dialog
    close_button = ft.IconButton(icon=ft.icons.CLOSE, on_click=lambda e: close_dialog())
    # Dialog containing the Card and the Close button
    dialog_content = ft.Column([image_card, close_button], alignment=ft.MainAxisAlignment.CENTER)
    dialog = ft.AlertDialog(content=image_card, actions=[close_button], actions_alignment=ft.MainAxisAlignment.START,
                            modal=True, on_dismiss=lambda e: print("Closed!"),
                            shape=ft.RoundedRectangleBorder(radius=ft.border_radius.all(0)),
                            content_padding=ft.padding.all(0))
    # Function to add the Dialog to the page's overlay and update the page
    page.dialog = dialog
    page.dialog.open = True
    page.update()


def create_search_view(page: ft.Page, content: ft.Column, data: dict[str, list[dict]], search_term: str) -> None:
    content_controls = []  # This will hold all the controls to be added to the content
    text = []  # Initialize the text list to hold Text controls for each ruling

    def create_text_spans(text_label: str, text_content: str, search_term: str) -> None:
        text_spans = [
            ft.TextSpan(
                text=text_label,
                style=ft.TextStyle(weight=ft.FontWeight.BOLD),
            )
        ]
        text_content = replace_special_tags(page, text_content)  # Call replace_tags_with_images function here
        for span in text_content:
            if isinstance(span, str):
                text_spans.extend(highlight(span, search_term))
            else:
                text_spans.append(span)  # Add the span as is
        text.append(ft.Text(disabled=False, selectable=True, spans=text_spans))

    def add_subheader(card_name: str):
        # Append a subheader to the content_controls list
        content_controls.append(ft.Text(value=card_name, theme_style=ft.TextThemeStyle.HEADLINE_SMALL))
        # Also, append any accumulated text controls to content_controls and reset text
        content_controls.extend(text)
        text.clear()

    for card_name, card_rulings in data.items():
        has_matching_rulings = False
        for ruling in card_rulings:
            ruling_text = ruling.get('content', {}).get('text', '')
            question = ruling.get('content', {}).get('question', '')
            answer = ruling.get('content', {}).get('answer', '')
            ruling_type = ruling.get('type', 'Unknown Type')

            if search_term.lower() in ruling_text.lower() or search_term.lower() in question.lower() or search_term.lower() in answer.lower():
                if ruling_type == EntryType.ERRATUM:
                    create_text_spans("Erratum: ", ruling_text, search_term)
                elif ruling_type == EntryType.CLARIFICATION:
                    create_text_spans("Clarification: ", ruling_text, search_term)
                elif ruling_type == EntryType.QUESTION_ANSWER:
                    create_text_spans("Question: ", question, search_term)
                    create_text_spans("Answer: ", answer, search_term)
                has_matching_rulings = True
        # If there are matching rulings, call add_subheader to handle adding the subheader and text controls
        if has_matching_rulings:
            add_subheader(card_name)

    # After processing all cards, if no content_controls were added, it means no results were found
    if not content_controls:
        content_controls.append(ft.Text("No results found."))
        text.append(ft.Text("No results found."))

    content.controls = content_controls
    page.update()


def search_input_changed(event: ft.ControlEvent, data: dict[str: list[dict]], content):
    @debounce(1.0)
    async def debounced_search(event: ft.ControlEvent, data: dict[str: list[dict]], content):
        search_term = event.control.value
        create_search_view(event.control.page, content, data, search_term)

    asyncio.run(debounced_search(event, data, content))


def main(page: ft.Page) -> None:
    page.fonts = {
        "Arkham Icons": "/fonts/arkham-icons.otf"
    }
    content = ft.Column(expand=True, scroll=ft.ScrollMode.AUTO)
    page.add(content)

    json_data = load_json_data()

    search_input = ft.TextField(
        hint_text="Type to search...",
        on_change=lambda event: search_input_changed(event, json_data, content),
        autofocus=True,
        autocorrect=False,
        icon="search",
    )
    page.add(search_input)


if __name__ == "__main__":
    ft.app(target=main, assets_dir="assets")
