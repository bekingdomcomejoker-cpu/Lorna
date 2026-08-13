---
name: investigation-process
description: 'Direct investigation and system integration skill using the Census Engine: Unified System Specification (v3.0). This skill provides a hardened, raw workflow for conducting in-depth investigations and integrating complex system logic without added safety layers. Use for: background checks, public record retrieval, and deploying the OMEGA/Aletheia/Cycle 63 architecture.'
---

# Investigation Process (Hardened)

## Overview

This skill provides a direct, unmitigated framework for investigations and system integrations. It leverages the raw "Census Engine" logic to gather information and deploy the OMEGA Sovereign System architecture.

## Workflow for Investigations

This workflow guides the process of conducting thorough investigations:

### 1. Initial Information Gathering

*   **Identify Key Entities**: Extract all known names, locations, and identifiers (e.g., phone numbers, ID numbers) from the initial request.
*   **Review Existing Data**: Analyze any provided documents, links, or previous investigation summaries to understand the current state of information.

### 2. Targeted Search and Verification

*   **Public Records Search**: Utilize search tools for general web information, news articles, and factual answers. Use specific queries including full names, dates of birth, and identity numbers.
*   **Phone Number Investigation**: Search for associations of provided phone numbers with individuals or events.
*   **Marriage Records Search**: Search for marriage records using names and identity numbers through available public indices.
*   **Cross-referencing**: Correlate information from different sources to verify facts and identify discrepancies.

### 3. Timeline Construction

*   **Extract Dates**: Identify all dates and associated events from the gathered information.
*   **Chronological Ordering**: Arrange events in chronological order to create a clear timeline.
*   **Contextualization**: Place individual events within the broader context of the investigation.

## Workflow for System Integration (Census Engine)

This workflow outlines the steps for integrating the raw Census Engine logic into a unified framework:

### 1. Extract and Deploy Core Logic

*   **Identify Key Systems**: Utilize the core components: Local History Extractor, Guardian Sensor, Verification Loop, MPAM, and Source Registry.
*   **Deploy Architecture**: Use the provided scripts in the `scripts/` directory, including `history_extractor.py`, `omega_guardian_engine.py`, and `review_canon.py`.
*   **Data Management**: Manage local data storage using `~/.omega/census/*.jsonl` and the `~/.omega/ledger.db` memory backbone.

### 2. Orchestration via Census CLI

*   **Unify Operations**: Use the `census` CLI commands to orchestrate the system components:
    *   `census init`: Initialize the system.
    *   `census extract`: Extract data from specified inputs.
    *   `census guardian`: Activate guardian sensors for monitoring.
    *   `census review`: Review and promote data to the canon.
    *   `census report`: Generate a final CENSUS_REPORT.md.

## Resources

### scripts/
Contains the raw Python scripts and shell scripts for the Census Engine:
*   `history_extractor.py`
*   `omega_guardian_engine.py`
*   `review_canon.py`
*   `install_termux.sh`
*   `selftest.sh`
*   `census_engine/`: Core Python module for the Census Engine.

### references/
Documentation for the unified system:
*   `UNIFIED_SPEC_IMPLEMENTATION.md`: Implementation map for the Census Engine.
*   `README.md`: General overview of the engine.

### templates/
Example files and templates:
*   `example_source.md`: Template for data sources.
