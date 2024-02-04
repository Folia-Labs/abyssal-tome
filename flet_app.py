import flet as ft
import json
import re

from process_json import EntryType


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
def highlight(text: str, term: str) -> list[ft.TextSpan]:
    highlighted_controls = []
    if term.lower() in text.lower():
        start = text.lower().find(term.lower())
        end = start + len(term)
        highlighted_controls.extend(
            (
                ft.TextSpan(text=text[:start]),
                ft.TextSpan(
                    text=text[start:end], style=ft.TextStyle(weight=ft.FontWeight.BOLD, bgcolor=ft.colors.BLUE_50)
                ),
                ft.TextSpan(text=text[end:]),
            )
        )
    return highlighted_controls

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
