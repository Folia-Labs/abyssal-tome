import flet as ft
import asyncio
import contextlib
import json
import re
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


def replace_tags_with_images(text: str) -> list:
    spans = []
    while any(tag in text for tag in TAG_TO_IMAGE):
        for tag, image_name in TAG_TO_IMAGE.items():
            if tag in text:
                index = text.index(tag)
                # Add the text before the tag as a TextSpan
                if index > 0:
                    spans.append(ft.TextSpan(text=text[:index]))
                # Add the image for the tag
                spans.append(ft.TextSpan(text=image_name, style=ft.TextStyle(size=20, font_family="Arkham Icons")))
                # Remove the processed part of the text
                text = text[index + len(tag):]
                break
    # Add any remaining text as a TextSpan
    if text:
        spans.append(ft.TextSpan(text=text))
    return spans


def create_search_view(page: ft.Page, content: ft.Column, data: dict[str, list[dict]], search_term: str) -> None:
    text = []

    def create_text_spans(text_label: str, text_content: str, search_term: str) -> None:
        text_spans = [
            ft.TextSpan(
                text=text_label,
                style=ft.TextStyle(weight=ft.FontWeight.BOLD),
            )
        ]
        text_content = replace_tags_with_images(text_content)  # Call replace_tags_with_images function here
        for span in text_content:
            if isinstance(span, str):
                text_spans.extend(highlight(span, search_term))
            else:
                text_spans.append(span) # Add the span as is
        text.append(ft.Text(disabled=False, selectable=True, spans=text_spans))

    for card_name, card_rulings in data.items():
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

    if not text:
        text.append(ft.Text("No results found."))

    content.controls = text
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
