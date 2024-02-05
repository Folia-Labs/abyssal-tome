import flet as ft
import asyncio
import contextlib
import json
import regex as re
import functools
from pathlib import Path

from process_json import EntryType

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
    with open('processed_data.json', 'r', encoding='utf-8') as file:
        data = json.load(file)
    return data


def mark_subheader(card_name: str) -> str:
    return f"## {card_name}"


# Function to highlight the search term in text
# It finds the search term in the text and then creates three ft.TextSpan objects:
# 1. The text before the search term
# 2. The search term itself
# 3. The text after the search term
# The search term is highlighted by setting its color to yellow
def highlight(text: str | ft.TextSpan, term: str) -> list:
    spans = []
    while text:
        if isinstance(text, str):
            if term.lower() in text.lower():
                start = text.lower().find(term.lower())
                end = start + len(term)
                spans.extend(
                    (
                        ft.TextSpan(
                            text=text[:start],
                        ),
                        ft.TextSpan(
                            text=text[start:end],
                            style=ft.TextStyle(
                                weight=ft.FontWeight.BOLD,
                                bgcolor=ft.colors.YELLOW_50,
                            ),
                        ),
                    )
                )
                text = text[end:]
            else:
                spans.append(ft.TextSpan(text=text))
                break
        else:
            spans.append(ft.TextSpan(text=text.text, style=text.style))
            text = text.spans
    return spans


LINK_PATTERN = re.compile(r"\[(.+?)\]\((.+?)\)")

import re
import flet as ft

TAG_PATTERN = re.compile('|'.join(re.escape(tag) for tag in TAG_TO_IMAGE))


def replace_special_tags(text: str) -> list[ft.TextSpan]:
    spans = []

    def process_match_parts(text, start, end):
        start_text = text
        if start > 0:
            start_text = text[:start]
            spans.append(ft.TextSpan(text=start_text))
        return start_text, start, end

    remaining_text = text
    while match := TAG_PATTERN.search(remaining_text):
        tag = match.group()
        image_name = TAG_TO_IMAGE[tag]
        remaining_text, start, end = process_match_parts(remaining_text, 0, match.start())
        spans.append(ft.TextSpan(text=image_name, style=ft.TextStyle(size=20, font_family="Arkham Icons")))
        remaining_text, _, _ = process_match_parts(remaining_text, start + len(tag), end)

    while match := LINK_PATTERN.search(remaining_text):
        link_text, link_url = match.groups()
        remaining_text, start, end = process_match_parts(remaining_text, 0, match.start())
        spans.append(ft.TextSpan(text=link_text, url=link_url))
        remaining_text, _, _ = process_match_parts(remaining_text, end, len(remaining_text))

    if remaining_text:
        spans.append(ft.TextSpan(text=remaining_text))
    return spans

    return spans


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
        text_content = replace_special_tags(text_content)  # Call replace_tags_with_images function here
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
