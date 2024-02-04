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


def highlight(text: str, term: str) -> str:
    return re.sub(fr'({term})', r'==\1==', text, flags=re.IGNORECASE)


def create_search_view(page: ft.Page, content: ft.Column, data: dict[str, list[dict]], search_term: str) -> None:
    highlighted_controls = []

    name_added = False
    for card_name, card_rulings in data.items():
        # card_name = ruling.get('card_name', 'Unknown Card')
        # card_code = ruling.get('card_code', 'Unknown Code')
        for ruling in card_rulings:
            ruling_text = ruling.get('content', {}).get('text', '')
            question = ruling.get('content', {}).get('question', '')
            answer = ruling.get('content', {}).get('answer', '')
            ruling_type = ruling.get('type', 'Unknown Type')

            if search_term.lower() in ruling_text.lower() or search_term.lower() in question.lower() or search_term.lower() in answer.lower():
                if not name_added:
                    highlighted_controls.append(ft.Markdown(value=mark_subheader(card_name), selectable=True, extension_set=ft.MarkdownExtensionSet.GITHUB_FLAVORED))

                if ruling_type == EntryType.ERRATUM:
                    highlighted_controls.append(ft.Markdown(value=highlight(f"**Erratum:** {ruling_text}" ,search_term), selectable=True))
                elif ruling_type == EntryType.CLARIFICATION:
                    highlighted_controls.append(ft.Markdown(value=highlight(f"**Clarification:** {ruling_text}" ,search_term), selectable=True))
                elif ruling_type == EntryType.QUESTION_ANSWER:
                    highlighted_controls.extend(
                        (
                            ft.Markdown(selectable=True,
                                value=highlight(
                                    f"**Question:** {question}", search_term
                                )
                            ),
                            ft.Markdown(selectable=True,
                                value=highlight(
                                    f"**Answer:** {answer}", search_term
                                )
                            ),
                        )
                    )
    if not highlighted_controls:
        highlighted_controls.append(ft.Markdown(value="No results found.", selectable=True))

    content.controls = highlighted_controls
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
    ft.app(target=main)
