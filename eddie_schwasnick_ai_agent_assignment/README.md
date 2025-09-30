# AI Data Collection Agent – Polygon.io Case Study

## Project Overview

This project implements an AI-powered data collection agent that interacts with the Polygon.io API to gather *reference* data on U.S.-listed equities. The agent follows a Data Management Plan (DMP) and demonstrates best practices in:

- Robust API interactions (requests, parameters, retries).
- Respectful data collection (rate limiting, jitter).
- Data validation, de-duplication, and basic quality scoring.
- Automated documentation (metadata, quality report, collection summary).
- Secure configuration (no hardcoded secrets).

**Data Collected (reference variables):**
- `ticker` — Stock or fund symbol (unique identifier).
- `name` — Company/fund name.
- `market` — Market type (e.g., `stocks`).
- `locale` — Market locale (e.g., `us`).
- `primary_exchange` — Primary listing exchange (e.g., `XNYS`, `XNAS`, `BATS`).

**Geographic Scope:** U.S.-listed equities (NYSE, Nasdaq, BATS, ARCA, etc.)  
**Time Range:** Current snapshot at collection time (reference data, not historical).

---

## Repository Structure

├── README.md # Project overview and instructions (this file)
├── data_management_plan.pdf # Mini-DMP (Part 1)
├── agent/
│ ├── data_collection_agent.py # Main agent class
│ ├── config.json # Configuration (no real keys in repo)
│ ├── data_collection.log # AI Agent run log
│ ├── agent_output.json # output from agent
│ ├── agent_quality_assurance/
│ └── agent_running.png # proof the agent runs
│ └── collection_summary.md # summary of what was collected
│ └── dataset_metadata.json # metadata of dataset
│ └── quality_report;json # quality report in json format
│ └── quality report.md # quality report in human readable .md format
├── data/
│ ├── api_test.py # test functions for api key
│ ├── api_test_output.json # test functions output using api
│ ├── config.json # config file with no real keys
│ ├── key_creation.png # proof a key was created
└── demo/
├── api_exercises.py # Part 2 exercises (2.2, 2.3)
│ ├── api_what_I_learned.pdf # paragraph explaining what I learned in the exercises
│ ├── demo_output/
│ └── cat_facts.json # 2.2 output
│ └── holidays.json # 2.3 output


The agent will:

Load configuration and API key.

Collect batches from Polygon.io with respectful delays.

Validate, de-duplicate, and store records.

Generate documentation: metadata, quality report, and collection summary.

Write logs showing adaptive strategy and delays
