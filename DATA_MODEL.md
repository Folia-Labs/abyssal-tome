# Abyssal Tome Data Models

This document describes the structure of the primary JSON data files used by Abyssal Tome.

## Main Rulings Data (`assets/processed_rulings_v3_ai_enriched.json`)

This file contains an array of `Ruling` objects. Each object represents a single ruling or Q&A pair.

### Ruling Object Structure

```json
{
  "id": "string (uuid)",
  "source_card_code": "string (5-digit card code, e.g., '01001', or '00000' for general)",
  "related_card_codes": ["string (card_code)", "..."],
  "ruling_type": "string (Enum: ERRATA, QUESTION_ANSWER, CLARIFICATION, etc.)",
  "question": "string | null (The question text, if type is QUESTION_ANSWER)",
  "answer": "string | null (The answer text, if type is QUESTION_ANSWER)",
  "text": "string | null (The ruling text, if not QUESTION_ANSWER)",
  "provenance": {
    "source_type": "string (e.g., 'arkhamdb_faq', 'official_faq_pdf', 'discord_community_ruling')",
    "source_name": "string | null (e.g., 'FAQ v1.7, March 2020', 'MJ Newman on Discord')",
    "source_date": "string | null (ISO date string, e.g., '2020-03-17T15:21:16.000Z' or 'YYYY-MM-DD')",
    "retrieval_date": "string (ISO datetime string, UTC)",
    "source_url": "string | null (URL to the source if available)"
  },
  "original_html_snippet": "string | null (The original HTML/text snippet this ruling was derived from)",
  "tags": ["string", "..."]
}
```

**Fields:**

*   `id`: A unique UUID string identifying the ruling.
*   `source_card_code`: The 5-digit code of the card this ruling was primarily found under or is most associated with. "00000" can indicate a general ruling not tied to a specific card.
*   `related_card_codes`: A list of other 5-digit card codes that this ruling pertains to or mentions.
*   `ruling_type`: An enum string indicating the type of ruling. Possible values include:
    *   `ERRATA`: Official correction to card text or game rules.
    *   `QUESTION_ANSWER`: A specific question and its answer.
    *   `CLARIFICATION`: General clarification of rules or interactions.
    *   `NOTE`: An important note or reminder.
    *   `UPDATE`: An update to a previous ruling or FAQ entry.
    *   `AS_IF`: Rulings pertaining to "as if" game mechanics.
    *   `AUTOMATIC_SUCCESS_FAILURE`: Rulings about automatic success/failure.
    *   (Other types as defined in `scripts/process_new_format.py:RulingType`)
*   `question`: If `ruling_type` is `QUESTION_ANSWER`, this field holds the question text. Otherwise, null.
*   `answer`: If `ruling_type` is `QUESTION_ANSWER`, this field holds the answer text. Otherwise, null.
*   `text`: If `ruling_type` is not `QUESTION_ANSWER` (e.g., `CLARIFICATION`, `ERRATA`), this field holds the main body of the ruling. Otherwise, null.
*   `provenance`: An object detailing the source of the ruling (see below).
*   `original_html_snippet`: The raw HTML or text snippet from which this specific ruling was parsed (e.g., the content of an `<li>` tag from ArkhamDB, or the raw text from a Discord message). Useful for debugging and context.
*   `tags`: A list of keywords or tags associated with the ruling (e.g., "timing_window", "player_cards", "mythos_phase"), often AI-generated or manually curated.

### Provenance Object Structure

```json
{
  "source_type": "string",
  "source_name": "string | null",
  "source_date": "string | null",
  "retrieval_date": "string (ISO datetime)",
  "source_url": "string | null"
}
```

*   `source_type`: Category of the source (e.g., `arkhamdb_faq`, `official_faq_pdf`, `email_ruling`, `discord_community_ruling`, `bgg_card_comment`).
*   `source_name`: Specific name of the source document or context (e.g., "FAQ v1.7, March 2020", "Matt Newman on Discord #rules channel", "BGG Comment on Machete").
*   `source_date`: The publication date of the source document or post (ISO format if possible, e.g., "2020-03-01", or "2022-08-29T13:11:03.000Z").
*   `retrieval_date`: The date and time (UTC) when this ruling was last fetched or processed into the system.
*   `source_url`: A direct URL to the ruling or source document, if available.

## Opinionated Rulings Data (`assets/opinionated_rulings.json`)

This file contains an array of `OpinionatedRuling` objects. These provide alternative interpretations, house rules, or community views related to official rulings.

### OpinionatedRuling Object Structure

```json
{
  "opinion_id": "string (uuid)",
  "applies_to_ruling_id": "string (uuid of an official ruling)",
  "opinion_text": "string (The full text of the opinionated ruling)",
  "opinion_summary": "string | null (A brief summary of the opinion)",
  "provenance": {
    "author": "string (Name of the individual, group, or community source)",
    "source_description": "string | null (e.g., 'MythosBusters Discord', 'Personal Blog')",
    "source_url": "string | null (Link to the discussion or source of the opinion)",
    "date_of_opinion": "string | null (ISO date, e.g., '2023-11-01')"
  },
  "tags": ["string", "..."],
  "replaces_official_text": "boolean (True if this opinion suggests replacing the official ruling)"
}
```

**Fields:**

*   `opinion_id`: A unique UUID string identifying this opinion.
*   `applies_to_ruling_id`: The `id` of the official ruling (from `processed_rulings_v3_ai_enriched.json`) that this opinion relates to.
*   `opinion_text`: The full text content of the opinionated ruling or interpretation.
*   `opinion_summary`: An optional short summary of the opinion's main point.
*   `provenance`: An object detailing the source of the opinion (see below).
*   `tags`: A list of keywords or tags for the opinion (e.g., `house_rule`, `controversial`, `popular_variant`, `balance_fix`).
*   `replaces_official_text`: Boolean. `true` if this opinion is intended as a direct replacement for the official text (e.g., a house rule that changes an official ruling). `false` if it's more of a clarification, commentary, or additional context.

### Opinion Provenance Object Structure

```json
{
  "author": "string",
  "source_description": "string | null",
  "source_url": "string | null",
  "date_of_opinion": "string | null"
}
```

*   `author`: The individual, group, or community that authored or champions this opinion.
*   `source_description`: A brief description of where this opinion comes from (e.g., "MythosBusters Discord #rules-discussion", "Our weekly playgroup").
*   `source_url`: A URL to the discussion, blog post, or source of the opinion, if available.
*   `date_of_opinion`: The approximate date this opinion was formulated or published.

## Data Processing Workflow Overview

1.  **ArkhamDB FAQ Scraping:** Rulings are scraped from ArkhamDB using `scripts/scrape_arkhamdb_faq.py`, which outputs `faqs/faqs.json`. This contains raw HTML content per card.
2.  **Initial Processing:** `scripts/process_new_format.py` reads `faqs/faqs.json`.
    *   It parses the HTML using BeautifulSoup.
    *   It identifies individual rulings (often from `<li>` tags or by parsing `<strong>` tags like "Q:", "A:", "Errata:").
    *   It extracts text, attempts to determine ruling type, and captures basic provenance (ArkhamDB source, card update date, linked card codes, and tries to find FAQ version strings).
    *   The output is `assets/processed_rulings_v2.json`.
3.  **AI Enrichment & External Data Integration:** `scripts/enrich_rulings_ai.py` takes `assets/processed_rulings_v2.json` as input.
    *   It also loads raw external rulings from `assets/raw_external_rulings.json`. These external rulings are first converted into the standard `Ruling` format, using AI placeholders to attempt Q&A extraction and provenance detailing.
    *   The combined list of rulings is then processed by (placeholder) AI functions to:
        *   Enhance `related_card_codes` (identify more card mentions).
        *   Refine `provenance` details.
        *   Generate `tags`.
    *   The output is `assets/processed_rulings_v3_ai_enriched.json`. This is the main data file used by the application.
4.  **Opinionated Rulings:** `assets/opinionated_rulings.json` is manually curated or generated by other means. It links to official ruling IDs.
