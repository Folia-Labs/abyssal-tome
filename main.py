import itertools
import logging
import sys
from enum import StrEnum, unique
from pathlib import Path

import flet as ft
import asyncio
import json
import regex as re
from functools import singledispatch
from gql import Client, gql
from gql.transport.aiohttp import AIOHTTPTransport as GQL_Transport

from utils import debounce

logging.basicConfig(level=logging.WARNING, stream=sys.stdout)


# from gql.utilities.build_client_schema import GraphQLSchema

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


TAG_TO_LETTER = {
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
TAG_PATTERN = re.compile('|'.join(re.escape(tag) for tag in TAG_TO_LETTER))

transport = GQL_Transport(url="https://gapi.arkhamcards.com/v1/graphql")
gql_client = Client(transport=transport, fetch_schema_from_transport=True)


def load_json_data() -> dict:
    with open(Path('assets/processed_data.json'), 'r', encoding='utf-8') as file:
        data = json.load(file)
    return data


@singledispatch
def highlight_text_span(text, term: str) -> list[ft.TextSpan]:
    raise ValueError("Unsupported text type for highlighting")


@highlight_text_span.register
def _(text: str, term: str) -> list[ft.TextSpan]:
    lower_text = text.lower()
    lower_term = term.lower()
    pattern = re.compile(re.escape(lower_term))
    spans = []
    remaining_text = lower_text
    while match := pattern.search(remaining_text):
        start, end = match.span()
        if start > 0:
            spans.append(ft.TextSpan(
                text=remaining_text[:start],
            )
            )

        spans.append(ft.TextSpan(
            text=text[match.start():match.end()],
            style=ft.TextStyle(
                weight=ft.FontWeight.BOLD,
                bgcolor=ft.colors.DEEP_ORANGE_50
            )
        ))

        remaining_text = remaining_text[end:]
        if remaining_text:
            spans.append(ft.TextSpan(text=remaining_text))

    return spans


@highlight_text_span.register
def _(text: ft.TextSpan, term: str) -> list[ft.TextSpan]:
    logging.info("Highlight function called with term: %s", term)
    if text.spans:
        logging.info("TextSpan has nested spans.")
        # If the TextSpan has nested spans, recursively highlight each nested span
        highlighted_spans = [highlight_text_span(span, term) for span in text.spans]
        # Flatten the list of highlighted_spans
        highlighted_spans = list(itertools.chain(*highlighted_spans))
        logging.info("Highlighted spans: %s", highlighted_spans)
        return [ft.TextSpan(spans=highlighted_spans, style=text.style)]
    else:
        logging.info("TextSpan does not have nested spans.")
        spans = []
        spans.extend(highlight_text_span(text.text, term))
        logging.info("Final spans: %s", spans)
        return spans


@highlight_text_span.register
def _(text: list, term: str) -> list[ft.TextSpan]:
    logging.warning(f"highlight_text_span called with term: {term}")
    highlighted_spans = []
    for span in text:
        highlighted_spans.extend(highlight_text_span(span, term))
    return highlighted_spans


def replace_special_tags(page: ft.Page, ruling_text: str) -> ft.Text:
    spans = []
    remaining_text = ruling_text
    if not remaining_text:
        logging.warning("replace_special_tags called with empty ruling_text.")

    # First, handle the LINK_PATTERN
    while re_match := LINK_PATTERN.search(remaining_text):
        start, end = re_match.span()
        if start > 0:
            spans.append(ft.TextSpan(text=remaining_text[:start], style=ft.TextStyle()))

        link_text, link_url = re_match.groups()
        card_id = link_url.split("/")[-1]
        spans.append(
            ft.TextSpan(
                text=link_text,
                style=ft.TextStyle(
                    decoration=ft.TextDecoration.UNDERLINE,
                    color=ft.colors.BLUE_ACCENT_400,
                    bgcolor=ft.colors.DEEP_ORANGE_50,
                ),
                on_click=lambda event, card_code=card_id: on_card_click(event, page, card_code)
            )
        )
        remaining_text = remaining_text[end:]

    # Then, handle the TAG_PATTERN
    while re_match := TAG_PATTERN.search(remaining_text):
        start, end = re_match.span()
        if start > 0:
            spans.append(ft.TextSpan(text=remaining_text[:start], style=ft.TextStyle()))

        tag = re_match.group()
        if tag not in TAG_TO_LETTER:
            logging.warning(f"Unsupported tag: {tag}")
            spans.append(ft.TextSpan(text=tag, style=ft.TextStyle()))
        else:
            tag_letter = TAG_TO_LETTER[tag]
            spans.append(
                ft.TextSpan(
                    text=tag_letter,
                    style=ft.TextStyle(
                        size=20,
                        font_family="Arkham Icons")
                )
            )

        remaining_text = remaining_text[end:]

    if remaining_text:
        spans.append(ft.TextSpan(text=remaining_text, style=ft.TextStyle()))


    if not spans:
        logging.error(f"No spans were created for ruling_text: {ruling_text}")

    return ft.Text(spans=spans)


async def on_card_click(event, page: ft.Page, card_id):
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
    if not image_url:
        logging.error(f"No image URL found for card_id: {card_id}")

    async def close_dialog():
        dialog.open = False  # Close the Dialog
        await page.close_dialog_async()
        page.dialog = None
        # dialog.visible = False  # Hide the Dialog

        await page.update_async()

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
    await page.update_async()


class SearchView:
    def __init__(self, page: ft.Page, data: dict[str, list[dict]]):
        self.page = page
        self.page_content: ft.Column = page.controls[0]
        self.data = data

    def create_text_spans(self, ruling_type: EntryType, search_term: str, ruling_text: str = "",
                          question_or_answer: QAType = None) -> ft.Text:
        if ruling_type == EntryType.QUESTION_ANSWER:
            if question_or_answer == QAType.QUESTION:
                ruling_type_name = "Question"
            elif question_or_answer == QAType.ANSWER:
                ruling_type_name = "Answer"
        else:
            ruling_type_name = ruling_type.title()

        text_spans = [
            ft.TextSpan(text=f"{ruling_type_name}: ", style=ft.TextStyle(weight=ft.FontWeight.BOLD))
        ]

        # Replace link and icon tags with their respective controls
        if not ruling_text:
            logging.warning(
                f"create_text_spans called with empty ruling_text for ruling_type: {ruling_type} and question_or_answer: {question_or_answer}")
            return ft.Text(disabled=False, selectable=True, spans=[])
        ruling_text_control = replace_special_tags(self.page, ruling_text)

        # Highlight the spans that match the search term
        for span in ruling_text_control.spans:
            text_spans.extend(highlight_text_span(span, search_term))
        return ft.Text(disabled=False, selectable=True, spans=text_spans)

    async def update_search_view(self, search_term: str) -> None:
        content_controls = []  # This will hold all the controls to be added to the content
        if not search_term:
            logging.warning("update_search_view called with empty search_term.")
        text = []  # Initialize the text list to hold Text controls for each ruling

        def add_subheader(card_name: str):
            # Append a subheader to the content_controls list
            content_controls.append(ft.Text(value=card_name, theme_style=ft.TextThemeStyle.HEADLINE_SMALL))
            # Also, append any accumulated text controls to content_controls and reset text
            content_controls.extend(text)
            text.clear()

        for card_name, card_rulings in self.data.items():
            for ruling in card_rulings:
                ruling_content = ruling.get('content', {})
                ruling_type = ruling.get('type', EntryType.UNKNOWN)
                ruling_text = ruling_content.get('text', '')
                ruling_question = ruling_content.get('question', '')
                ruling_answer = ruling_content.get('answer', '')

                if ruling_type == EntryType.QUESTION_ANSWER and (not ruling_question or not ruling_answer):
                    logging.warning(
                        f"Question/Answer ruling is missing content for card: {card_name=} {ruling_question=} {ruling_answer=}")

                if not any(re.search(search_term.lower(), text.lower()) for text in
                           [ruling_text, ruling_question, ruling_answer]):
                    continue

                if not ruling_text.strip() and not ruling_question.strip() and not ruling_answer.strip():
                    logging.warning(f"Ruling content is empty for card: {card_name}")
                    continue
                match ruling_type:
                    case EntryType.UNKNOWN:
                        logging.warning(
                            f"Unknown ruling type for card {card_name=}. Ruling type: {ruling_type=} Ruling text: {ruling_text, ruling_question, ruling_answer=} ")
                        text.append(ft.Text(ruling_text))
                    case EntryType.ERRATUM:
                        text.append(self.create_text_spans(ruling_type, search_term, ruling_text))
                    case EntryType.QUESTION_ANSWER:
                        if ruling_question:
                            text.append(
                                self.create_text_spans(ruling_type, search_term, ruling_question, QAType.QUESTION))
                        if ruling_answer:
                            text.append(self.create_text_spans(ruling_type, search_term, ruling_answer, QAType.ANSWER))
                    case EntryType.CLARIFICATION:
                        text.append(
                            self.create_text_spans(ruling_type, search_term, ruling_text))

                add_subheader(card_name)

        # After processing all cards, if no content_controls were added, it means no results were found
        if not content_controls:
            logging.info("No search results found for term: " + search_term)
            content_controls.append(ft.Text("No results found."))
            text.append(ft.Text("No results found."))

        self.page_content.controls = []  # Clear the content controls
        self.page_content.controls += content_controls
        await self.page.update_async()


class SearchInputChanged:
    def __init__(self, data: dict[str, list[dict]]):
        self.data = data

    async def search_input_changed(self, event: ft.ControlEvent):
        @debounce(1.0)
        async def debounced_search():
            search_term = event.control.value
            search_view = SearchView(event.control.page, self.data)
            if search_term:
                await search_view.update_search_view(search_term)

        # Schedule the debounced_search coroutine to run on the event loop
        await debounced_search()


async def main(page: ft.Page) -> None:
    page.fonts = {
        "Arkham Icons": "/fonts/arkham-icons.otf"
    }
    page_content = ft.Ref[ft.Column]()

    await page.add_async(ft.Column(ref=page_content, expand=True, scroll=ft.ScrollMode.AUTO))

    json_data = load_json_data()

    search_input_handler = SearchInputChanged(json_data)

    async def on_search_input_changed(event: ft.ControlEvent):
        await search_input_handler.search_input_changed(event)

    search_input = ft.TextField(
        hint_text="Type to search...",
        on_change=lambda event: asyncio.create_task(search_input_handler.search_input_changed(event)),
        autofocus=True,
        autocorrect=False,
        icon="search",
    )
    await page.add_async(search_input)
    await page.update_async()


if __name__ == "__main__":
    ft.app(target=main, assets_dir="assets", name="FAQthis!")
