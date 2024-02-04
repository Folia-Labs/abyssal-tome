import flet as ft
import json
import re


def load_json_data() -> dict:
    with open('processed_data.json', 'r', encoding='utf-8') as file:
        data = json.load(file)
    return data


def mark_subheader(text: str) -> str:
    return f"## {text}"


def highlight(text: str, term: str) -> str:
    return re.sub(fr'({term})', r'**\1**', text, flags=re.IGNORECASE)


def create_search_view(page: ft.Page, content: ft.Column, data: dict, search_term: str) -> None:
    highlighted_controls = []

    for card_name, rulings in data.items():
        card_name_added = False
        for ruling in rulings:
            if search_term.lower() in ruling.lower():
                if not card_name_added:
                    highlighted_controls.append(ft.Markdown(value=mark_subheader(card_name)))
                    card_name_added = True
                highlighted_controls.append(ft.Markdown(value=highlight(ruling, search_term)))

    if not highlighted_controls:
        highlighted_controls.append(ft.Text(value="No results found."))

    content.controls = highlighted_controls
    page.update()


def search_input_changed(event, data, content):
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
