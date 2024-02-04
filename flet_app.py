import flet as ft
import json
import re
from pathlib import Path

from process_json import EntryType

ICON_PATH = Path("icons/arkham")
TAG_TO_IMAGE = {
    "[willpower]": "willpower.png",
    "[agility]": "agility.png",
    "[combat]": "combat.png",
    "[intellect]": "intellect.png",
    "[skull]": "skull.png",
    "[cultist]": "cultist.png",
    "[tablet]": "tablet.png",
    "[elderthing]": "elderthing.png",
    "[autofail]": "autofail.png",
    "[eldersign]": "eldersign.png",
    "[bless]": "bless.png",
    "[curse]": "curse.png",
    "[frost]": "frost.png",
    "[reaction]": "reaction.png",
    "[unique]": "unique.png",
    "[mystic]": "mystic.png",
    "[guardian]": "guardian.png",
    "[seeker]": "seeker.png",
    "[rogue]": "rogue.png",
    "[free]": "free.png",
    "[activate]": "activate.png",
}

# Function to highlight the search term in text
# It finds the search term in the text and then creates three ft.TextSpan objects:

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
def highlight(text: str, term: str) -> list:
    spans = []
    term_lower = term.lower()
    while text:
        if term_lower in text.lower():
            start = text.lower().find(term_lower)
            end = start + len(term)
            spans.extend(replace_tags_with_images(text[:start]))
            spans.append(
                ft.TextSpan(
                    text=text[start:end],
                    style=ft.TextStyle(weight=ft.FontWeight.BOLD, bgcolor=ft.colors.BLUE_50)
                )
            )
            text = text[end:]
        else:
            spans.extend(replace_tags_with_images(text))
            break
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
                spans.append(ft.Image(src=str(ICON_PATH / image_name)))
                # Remove the processed part of the text
                text = text[index + len(tag):]
                break
    # Add any remaining text as a TextSpan
    if text:
        spans.append(ft.TextSpan(text=text))
    return spans

def create_search_view(page: ft.Page, content: ft.Column, data: dict[str, list[dict]], search_term: str) -> None:
    text = []
    text_spans = []

    name_added = False
    for card_name, card_rulings in data.items():
        for ruling in card_rulings:
            ruling_text = ruling.get('content', {}).get('text', '')
            question = ruling.get('content', {}).get('question', '')
            answer = ruling.get('content', {}).get('answer', '')
            ruling_type = ruling.get('type', 'Unknown Type')

            if search_term.lower() in ruling_text.lower() or search_term.lower() in question.lower() or search_term.lower() in answer.lower():
                if not name_added:
                    text.append(
                        ft.Text(
                            value=card_name,
                            disabled=False,
                            selectable=True,
                            theme_style=ft.TextThemeStyle.HEADLINE_SMALL,
                        )
                    )

                if ruling_type == EntryType.ERRATUM:
                    text_spans = [
                        ft.TextSpan(
                            text="Erratum: ",
                            style=ft.TextStyle(weight=ft.FontWeight.BOLD),
                        )
                    ]
                    text_spans.extend(highlight(ruling_text, search_term))
                    text.append(ft.Text(disabled=False, selectable=True, spans=text_spans) )
                elif ruling_type == EntryType.CLARIFICATION:
                    text_spans = [
                        ft.TextSpan(
                            text="Clarification: ",
                            style=ft.TextStyle(weight=ft.FontWeight.BOLD),
                        )
                    ]
                    text_spans.extend(highlight(ruling_text, search_term))
                    text.append(ft.Text(disabled=False, selectable=True, spans=text_spans))

                elif ruling_type == EntryType.QUESTION_ANSWER:
                    text_spans = [
                        ft.TextSpan(
                            text="Question: ",
                            style=ft.TextStyle(weight=ft.FontWeight.BOLD),
                        )
                    ]
                    text_spans.extend(
                        highlight(question, search_term)
                    )
                    text_spans.append(ft.TextSpan(text="\n"))
                    text_spans.append(
                        ft.TextSpan(
                            text="Answer: ",
                            style=ft.TextStyle(weight=ft.FontWeight.BOLD)
                        )
                    )
                    text_spans.extend(
                        highlight(answer, search_term)
                    )
                    text.append(ft.Text(disabled=False, selectable=True, spans=text_spans))

    if not text:
        text.append(ft.Text("No results found."))

    content.controls = text
    page.update()


def search_input_changed(event, data: dict[str: list[dict]], content):
    search_term = event.control.value
    create_search_view(event.control.page, content, data, search_term)


def main(page: ft.Page) -> None:
    content = ft.Column(expand=True, scroll=ft.ScrollMode.AUTO)
    page.add(content)

    json_data = load_json_data()

    search_input = ft.TextField(
        hint_text="Type to search...",
        on_change=lambda event: search_input_changed(event, json_data, content),
        autofocus=True
    )
    page.add(search_input)


if __name__ == "__main__":
    ft.app(target=main, assets_dir="icons")
