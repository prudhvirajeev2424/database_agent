# SQL AI Agent

An AI-powered natural language to SQL system that converts user questions into validated SQL queries and returns structured results.

**Stack:** Python · Azure OpenAI · MySQL / PostgreSQL / SQLite · Multi-Agent Architecture

---

## Overview

This system uses a multi-agent pipeline to process natural language questions:

```
User Question (CLI)
    ↓
Clarification Agent (if ambiguous)
    ↓
Query Generator Agent
    ↓
Technical Validator Agent
    ↓
Execution Engine (safe SQL execution)
    ↓
Response Agent
    ↓
Result Output
```

---

## Features

- **Multi-Agent Pipeline** – Clarification, query generation, validation, and formatting
- **Schema-Aware** – Understands database structure for context-relevant queries
- **Pluggable Databases** – MySQL, PostgreSQL, SQLite support via adapter pattern
- **Conversation Memory** – Maintains session context across queries
- **CLI Interface** – Simple interactive terminal-based input

---

## Project Structure

```
app/
├── agents/                    # LLM-based agents
│   ├── clarification_agent.py
│   ├── query_generator_agent.py
│   ├── technical_validator_agent.py
│   ├── response_agent.py
│   └── langchain_tools.py
├── application/               # Core orchestration
│   ├── orchestrator.py
│   ├── execution_engine.py
│   ├── conversation_manager.py
│   └── schema_registry.py
├── infrastructure/            # Data layer
│   ├── llm_client.py
│   ├── logger.py
│   └── db_adapters/
│       ├── mysql_adapter.py
│       ├── postgres_adapter.py
│       └── sqlite_adapter.py
├── presentation/              # UI layer
│   └── cli.py
└── config.py

database/
├── schema.sql
└── seed_data.sql

scripts/                        # Utility scripts
└── test_*.py
```

---

## Setup

```bash
pip install -r requirements.txt
```

Set your environment variables:
```
OPENAI_API_KEY=<your-key>
OPENAI_API_TYPE=azure
OPENAI_API_VERSION=2024-02-15-preview
OPENAI_API_ENDPOINT=<your-endpoint>
DB_TYPE=mysql  # or postgres, sqlite
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=password
DB_NAME=your_database
```

---

## Run

```bash
python main.py
```

