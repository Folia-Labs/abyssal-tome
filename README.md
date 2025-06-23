# Abyssal Tome

**Abyssal Tome (AT)** is a Python-powered application for Arkham Horror: The Card Game. It provides a comprehensive and easily searchable database of game rulings, FAQs, and clarifications, sourced from official documents, ArkhamDB, and community discussions.

This project aims to:
*   Consolidate rulings from diverse sources.
*   Improve the clarity and searchability of rulings.
*   Establish clear provenance for each ruling.
*   Allow for community contributions, including "opinionated" or alternative interpretations of rulings.
*   Leverage modern data processing techniques (and AI placeholders) for robust parsing and enrichment.

## Features (Post-Revamp)

*   **Unified Rulings Database:** Access official FAQs, ArkhamDB entries, and curated community rulings in one place.
*   **Enhanced Search:** Find rulings related to specific cards, even if the ruling wasn't originally posted under that card.
*   **Clear Provenance:** Each ruling details its source (e.g., specific FAQ version, website, community post), date, and retrieval information.
*   **Opinionated Rulings:** View community-sourced alternative interpretations or house rules alongside official rulings.
*   **Structured Data:** Rulings are parsed into a consistent JSON format, separating questions, answers, and errata. (See [DATA_MODEL.md](DATA_MODEL.md) for details).

## Data Pipeline Overview

The rulings data is generated through a multi-step pipeline:

1.  **ArkhamDB FAQ Scraping:**
    *   Script: `scripts/scrape_arkhamdb_faq.py`
    *   Output: `faqs/faqs.json` (raw HTML content per card from ArkhamDB's FAQ API).
2.  **Initial Processing & Structuring:**
    *   Script: `scripts/process_new_format.py`
    *   Input: `faqs/faqs.json`
    *   Action: Parses HTML, identifies individual rulings, extracts text, determines ruling type, and captures basic provenance (ArkhamDB source, card update date, linked card codes, FAQ version strings).
    *   Output: `assets/processed_rulings_v2.json`.
3.  **AI Enrichment & External Data Integration:**
    *   Script: `scripts/enrich_rulings_ai.py`
    *   Inputs:
        *   `assets/processed_rulings_v2.json` (from previous step)
        *   `assets/raw_external_rulings.json` (manually curated raw text from other sources like BGG, Discord)
    *   Action:
        *   Converts raw external rulings into the standard `Ruling` format.
        *   Uses (currently placeholder) AI functions to:
            *   Enhance `related_card_codes` (identifying more card mentions).
            *   Refine `provenance` details.
            *   Generate `tags` for better categorization.
            *   Attempt to structure raw text into Q&A where applicable.
    *   Output: `assets/processed_rulings_v3_ai_enriched.json`. This is the primary data file used by the application.
4.  **Opinionated Rulings:**
    *   File: `assets/opinionated_rulings.json`
    *   Content: Manually curated or community-contributed alternative interpretations that link to official ruling IDs from `processed_rulings_v3_ai_enriched.json`.

For a detailed description of the JSON structures, please see [DATA_MODEL.md](DATA_MODEL.md).

## Running the Data Processing Scripts

To regenerate the processed data files:

1.  Ensure Python environment and dependencies are set up (details TBD based on final libraries).
2.  Run the scraping script (if new ArkhamDB data is needed):
    ```bash
    python scripts/scrape_arkhamdb_faq.py
    ```
3.  Run the initial processing script:
    ```bash
    python scripts/process_new_format.py
    ```
4.  Run the enrichment script:
    ```bash
    python scripts/enrich_rulings_ai.py
    ```
    (Note: AI functionalities are currently placeholders. Real AI integration would require API keys and relevant libraries.)

## Adding New Rulings or Sources

There are two main ways to add new information:

**1. Adding External Rulings (e.g., from Discord, BGG, old emails):**

*   Open `assets/raw_external_rulings.json`.
*   Add a new JSON object to the array with the following fields:
    *   `source_type_hint`: A string indicating the general origin (e.g., "discord_mythosbusters_rules", "bgg_card_comment", "ffg_email_reply"). This helps the processing script.
    *   `source_url_or_context`: A URL to the post, or a brief description of the context (e.g., "Email from MJ Newman regarding Machete, circa 2017").
    *   `raw_text`: The full, raw text of the ruling or discussion. Include as much context as possible (e.g., who asked, who answered, dates if visible).
    *   `retrieved_by`: Your name/handle.
    *   `retrieval_date_utc`: The ISO 8601 date (e.g., "2024-03-15T10:00:00Z") when you added this entry.
*   Example:
    ```json
    {
      "source_type_hint": "discord_mythosbusters_rules",
      "source_url_or_context": "https://discord.com/channels/.../message_id",
      "raw_text": "User123: Can card X do Y?\nDesignerBob: Yes, under circumstance Z. (Jan 1, 2024)",
      "retrieved_by": "YourName",
      "retrieval_date_utc": "2024-03-16T12:00:00Z"
    }
    ```
*   After adding to `raw_external_rulings.json`, run `python scripts/enrich_rulings_ai.py` to process it into the main dataset. The AI (currently placeholder) will attempt to structure it. Manual review of the output in `processed_rulings_v3_ai_enriched.json` might be needed.

**2. Adding Opinionated Rulings:**

*   First, identify the `id` of the official ruling (from `processed_rulings_v3_ai_enriched.json`) that your opinionated ruling applies to.
*   Open `assets/opinionated_rulings.json`.
*   Add a new JSON object to the array following the structure defined in [DATA_MODEL.md](DATA_MODEL.md#opinionatedruling-object-structure).
*   Key fields include:
    *   `opinion_id`: Generate a new UUID (e.g., using an online UUID generator).
    *   `applies_to_ruling_id`: The ID of the official ruling.
    *   `opinion_text`: Your full opinion/house rule.
    *   `provenance`: Who authored this opinion, where it's from.
    *   `tags`: Relevant keywords.
    *   `replaces_official_text`: `true` or `false`.
*   The application should pick up these changes on the next data load.

## Development & Future Enhancements

*   **Actual AI Integration:** Replace placeholder AI functions in `scripts/enrich_rulings_ai.py` with calls to a real LLM (e.g., OpenAI, Anthropic models) for more accurate and powerful data enrichment.
*   **Web Application UI:** Enhance the Python web application to fully utilize the new data structures, improve search, and display opinionated rulings effectively.
*   **Database Backend:** For larger datasets or more complex querying, migrate from JSON files to a proper database (e.g., SQLite, PostgreSQL). The script `process_json_to_SQLite.py` is an old artifact indicating this direction was considered.
*   **Automated Scrapers:** Develop more robust scrapers for sources like BGG or specific Discord channels (requires careful handling of terms of service and ethical considerations).
*   **Community Contribution Interface:** A web interface for submitting new raw rulings or opinions directly, potentially with a review queue.
*   **AGENTS.md:** The project does not currently have an `AGENTS.md` file. If one is added, automated agents working on this codebase should adhere to its instructions.

## Original README Content
(The project was previously described as "Abysmal Templating" - this reflects its origins in tackling complex game text.)

AT - Abyssal Tome (AKA "Abysmal Templating") is a Python app for Arkham Horror: The Card Game, providing a quick way to search through the labyrinthine rulings that define how the game works. The rules and yearly FAQ's don't cover numerous rules questions and card interactions, and the responses to those enquiries are often lost to the void.
