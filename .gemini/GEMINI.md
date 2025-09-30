# GEMINI.MD: AI Collaboration Guide

This document provides essential context for AI models interacting with the web-ui project. Adhering to these guidelines will ensure consistency and maintain code quality in this unified AI research platform.

## 1. Project Overview & Purpose

* **Primary Goal:** This project is a full-stack unified AI research platform designed to integrate Python-based backend services (e.g., agent orchestration, browser automation) with a React frontend for real-time AI interactions. It supports features like deep research, document editing, and MCP (Model Context Protocol) tool servers, enabling seamless AI-driven workflows such as chat, browser control, and database management via ChromaDB.
* **Business Domain:** AI Research and Development, with applications in automation, data processing, and intelligent agent systems.

## 2. Core Technologies & Stack

* **Languages:** Python 3.13+ (backend), TypeScript/JavaScript (frontend), with potential Rust for MCP servers.
* **Frameworks & Runtimes:** FastAPI (backend for async APIs and WebSocket support), React 18 with TypeScript (frontend for UI), Node.js 18+ (frontend runtime).
* **Databases:** ChromaDB for vector storage and retrieval, integrated for persistent data management.
* **Key Libraries/Dependencies:** Backend: browser-use (browser automation), langchain-* (AI agents like MistralAI, IBM), pydantic (data validation), uvicorn (server). Frontend: Zustand (state management), React Router (navigation), Axios (API client). MCP: langchain_mcp_adapters for protocol integration. Other: ag-ui-protocol (for API compatibility), Gradio (legacy UI components).
* **Package Manager(s):** uv (Python dependencies, e.g., `uv add`, `uv sync`), npm/pnpm (Node.js for frontend).

## 3. Architectural Patterns

* **Overall Architecture:** Full-stack application with a clear separation of concerns: Python backend for API logic, agent orchestration, and database handling; React frontend for user interfaces; and MCP servers for tool integration. Follows a modular structure with async/await for real-time features like WebSockets. Inferred as a hybrid of monolithic (core backend/frontend) and microservices (MCP servers) for flexibility.
* **Directory Structure Philosophy:**
  * `backend/`: Houses Python source code (e.g., `src/web_ui/` for agents, APIs, database).
  * `frontend/`: Contains React source code (e.g., `src/` for components, hooks, stores).
  * `mcp/`: Dedicated to Model Context Protocol servers, organized by language (e.g., `ToolRack/Python/`, `ToolRack/TypeScript/`).
  * `data/`: Stores persistent data like ChromaDB files, documents, and configs (e.g., `mcp.json`).
  * `logs/`: Centralized logging (e.g., `web-ui.log` for main app logs).
  * `plans/`, `scripts/`, `tests/`: Supporting directories for project planning, automation, and testing.

## 4. Coding Conventions & Style Guide

* **Formatting:** Backend: Ruff formatter (configured via `ruff.toml` or `pyproject.toml`) with Black-style (line length 88, hanging commas). Frontend: ESLint/Prettier (assumed via React standards) for consistent indentation (e.g., 2 spaces). Use f-strings for Python string formatting.
* **Naming Conventions:** Backend: PEP 8 (snake_case for variables/functions, PascalCase for classes). Frontend: camelCase for variables/functions, PascalCase for components/classes, kebab-case for files (e.g., `my-component.tsx`).
* **API Design:** RESTful with FastAPI; uses standard HTTP methods (GET, POST, PUT, DELETE) and JSON for requests/responses. WebSocket for real-time updates.
* **Error Handling:** Use specific exception catching (e.g., try/except in Python) with full context re-raising. Avoid generic `except` blocks. Log errors to `logs/` with structured formats.

## 5. Key Files & Entrypoints

* **Main Entrypoint(s):** Backend: `backend/src/web_ui/main.py` (orchestrator). Frontend: `frontend/src/main.tsx`. Legacy: `webui.py` (Gradio-based UI).
* **Configuration:** Backend: `pyproject.toml` (dependencies, scripts). Frontend: `package.json` (assumed for npm setup). Global: `data/mcp.json` (MCP server config), `.env` (environment variables).
* **CI/CD Pipeline:** Not explicitly identified; inferred as potential GitHub Actions or similar for deployment (e.g., via `scripts/` or Docker files like `Dockerfile`, `docker-compose.yml`).

## 6. Development & Testing Workflow

* **Local Development Environment:** Backend: Run from `backend/` using `uv run` (e.g., `uv run uvicorn`). Frontend: From `frontend/` using `npm run dev` (port 3000). Use `start-dev.bat` or `start-dev.sh` for full-stack startup. Ensure logs write to `logs/`.
* **Testing:** Backend: pytest from project root (e.g., `pytest tests/`). Frontend: Assumed Jest or similar via npm scripts. Include unit/integration tests for new features.
* **CI/CD Process:** Commit to version control triggers builds (inferred from `Dockerfile`); uses supervisord for process management. Monitor for dependency updates via `uv.lock` and `package-lock.json`.

## 7. Specific Instructions for AI Collaboration

* **Contribution Guidelines:** Follow the project's modular structure—maintain separation between backend, frontend, and MCP. Use relative imports within sections and absolute for cross-section communication. Sign off commits with clear messages (e.g., "feat: add new agent adapter").
* **Infrastructure (IaC):** No dedicated IaC directory (e.g., `/iac`); changes to deployment files (e.g., `Dockerfile`) affect runtime and should be reviewed carefully.
* **Security:** Never hard-code secrets—use environment variables or vaults. Sanitize inputs, handle errors specifically, and ensure JWT/auth logic (e.g., via python-jose) is secure.
* **Dependencies:** Add via `uv add` for Python or `npm install` for Node.js. Update `pyproject.toml` or `package.json` accordingly; run `uv sync` or `npm install` to apply.
* **Commit Messages:** Use Conventional Commits (e.g., `feat:`, `fix:`, `docs:`) for clarity.

This GEMINI.md is inferred from the project's structure and rules with high confidence for most sections (e.g., based on `pyproject.toml` and directory layout). For unconfirmed details (e.g., exact frontend package versions), please review and update as needed. It builds on your existing `.gemini/GEMINI.md` task log by incorporating recent changes like ag-ui protocol integration.
