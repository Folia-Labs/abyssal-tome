import flet as ft
import pytest
import regex as re

from main import replace_special_tags

# Constants used in the tests
LINK_PATTERN = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
TAG_PATTERN = re.compile(r"\{([^}]+)\}")
TAG_TO_LETTER = {"{bold}": "B", "{italic}": "I"}


# Mock functions
def on_card_click(event, page, card_id) -> None:
    """
    Placeholder for a card click event handler.
    
    Intended to handle actions when a card is clicked, receiving the event, page context, and card identifier.
    """
    pass


def append_span(spans, text, style=None, on_click=None) -> None:
    """
    Appends a TextSpan with optional style and click handler to the provided spans list.
    
    Parameters:
        spans (list): The list to which the TextSpan will be appended.
        text (str): The text content for the TextSpan.
        style (optional): The style to apply to the TextSpan.
        on_click (optional): The click handler function for the TextSpan.
    """
    span = ft.TextSpan(text=text, style=style, on_click=on_click)
    spans.append(span)


@pytest.mark.parametrize(
    "test_id, ruling_text, expected_spans_length, expected_warnings, expected_errors",
    [
        # Happy path tests
        ("HP-1", "[Link](http://example.com/card1)", 1, 0, 0),
        ("HP-2", "{bold}Bold Text", 1, 0, 0),
        (
            "HP-3",
            "Normal text with [Link](http://example.com/card2) and {italic}Italic Text",
            3,
            0,
            0,
        ),
        # Edge cases
        ("EC-1", "", 0, 1, 0),  # Empty ruling_text
        ("EC-2", "No special tags here", 1, 0, 1),  # Text without any tags
        # Error cases
        ("ER-1", "{unsupported}Unsupported tag", 1, 1, 0),  # Unsupported tag
        (
            "ER-2",
            "[Link](http://example.com/) and {unsupported}Unsupported tag",
            2,
            1,
            0,
        ),  # Mixed content
    ],
)
def test_replace_special_tags(
    test_id, ruling_text, expected_spans_length, expected_warnings, expected_errors, caplog
) -> None:
    # Arrange
    """
    Test the replace_special_tags function for correct span creation and logging behavior.
    
    Verifies that the number of spans, warnings, and errors produced by replace_special_tags matches expectations for various input scenarios.
    """
    page = ft.Page()

    # Act
    spans = replace_special_tags(page, ruling_text)

    # Assert
    assert len(spans) == expected_spans_length, (
        f"Test ID {test_id}: Unexpected number of spans created."
    )
    assert (
        len([record for record in caplog.records if record.levelname == "WARNING"])
        == expected_warnings
    ), f"Test ID {test_id}: Unexpected number of warnings."
    assert (
        len([record for record in caplog.records if record.levelname == "ERROR"]) == expected_errors
    ), f"Test ID {test_id}: Unexpected number of errors."
