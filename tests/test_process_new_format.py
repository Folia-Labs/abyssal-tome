import contextlib

import pytest
from bs4 import BeautifulSoup
from hypothesis import given
from hypothesis.strategies import text
from pydantic import ValidationError

from scripts.process_new_format import Ruling, RulingType, process_ruling_html


def test_process_ruling_html_empty_input() -> None:
    empty_soup = BeautifulSoup("", "html.parser")
    result = process_ruling_html("00000", empty_soup, None)
    assert result == []


def test_process_ruling_html_with_valid_input() -> None:
    html_content = """
    <strong>Errata:</strong> Corrected text.
    <strong>Q:</strong> Question text?
    <strong>A:</strong> Answer text.
    """
    soup = BeautifulSoup(html_content, "html.parser")
    result = process_ruling_html("00000", soup, None)
    assert len(result) == 2
    assert result[0].ruling_type == RulingType.ERRATA
    assert result[1].ruling_type == RulingType.QUESTION_ANSWER
    assert result[0].text == "Corrected text."
    assert result[1].question == "Question text?"
    assert result[1].answer == "Answer text."


def test_process_ruling_html_combines_q_and_a() -> None:
    html_content = """
    <strong>Q:</strong> Question text?
    <strong>A:</strong> Answer text.
    """
    soup = BeautifulSoup(html_content, "html.parser")
    result = process_ruling_html("00000", soup, None)
    assert len(result) == 1
    assert result[0].ruling_type == RulingType.QUESTION_ANSWER
    assert result[0].question == "Question text?"
    assert result[0].answer == "Answer text."


@pytest.mark.parametrize(
    "input_html,expected_ruling_types",
    [
        ("<strong>Errata:</strong> Some text.", [RulingType.ERRATA]),
        ("<strong>Q:</strong> Question? <strong>A:</strong> Answer.", [RulingType.QUESTION_ANSWER]),
        ("<strong>Clarification:</strong> Clarification text.", [RulingType.CLARIFICATION]),
    ],
)
def test_process_ruling_html_various_types(input_html, expected_ruling_types) -> None:
    soup = BeautifulSoup(input_html, "html.parser")
    result = process_ruling_html("00000", soup, None)
    assert len(result) == len(expected_ruling_types)
    for ruling, expected_type in zip(result, expected_ruling_types, strict=False):
        assert ruling.ruling_type == expected_type


@given(question=text(), answer=text())
def test_question_ruling_with_hypothesis(question, answer) -> None:
    with contextlib.suppress(ValidationError):
        ruling = Ruling(source_card_code="00000", provenance={"source_type": "test"}, ruling_type=RulingType.QUESTION_ANSWER, question=question, answer=answer)
        assert ruling.question == question
        assert ruling.answer == answer
