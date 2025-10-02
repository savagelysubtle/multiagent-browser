awesome — i read through your project digest and put together a clean, repo-specific `agents.md` you can drop into `mcp/server/` (or wherever you keep docs). It documents the agents you already expose via `/.well-known`, the API routes in your FastAPI service, and how to add new agents.

---

# agents.md

## Overview

This project ships a small catalog of AI "agents" (specialized capabilities) that can be discovered via a public **`/.well-known` registry** and invoked through the backend API. The catalog currently includes:

* **Browser Use Agent** — navigates and interacts with web pages.
* **Deep Research Agent** — runs multi-step research with verification.
* **Document Editor Agent** — creates/edits documents with context.

Discovery follows the web standard for **well-known URIs** (paths under `/.well-known/`) so client apps can find agent cards in a predictable location. ([RFC Editor][1])

Some workflows reference **LangGraph** for long-running, stateful research flows. If you're new to it, LangGraph is a stateful orchestration framework for agentic apps (Python & JS). ([LangChain Docs][2])

> Note: If you're integrating with broader agent ecosystems, this repo also aligns with modern "agent protocol" practices (e.g., MCP) for connecting apps to tools and data. ([Model Context Protocol][3])

---

## Directory layout

```
.well-known/
  agents.json                 # registry index
  agents/
    browser_use.json          # agent card
    deep_research.json        # agent card
    document_editor.json      # agent card

backend/src/web_ui/api/
  ├── server.py                     # FastAPI app with lifespan management
  ├── dependencies.py               # Dependency injection for agents
  ├── routes/
  │   ├── agents.py                 # Main agents API router
  │   ├── auth.py                   # Authentication routes
  │   ├── documents.py              # Document management
  │   ├── ag_ui.py                  # AG-UI integration
  │   ├── copilotkit.py             # CopilotKit integration
  │   ├── dev_routes.py             # Development utilities
  │   └── logging.py                # Frontend logging
  ├── middleware/
  │   └── error_handler.py          # Global error handling
  ├── websocket/
  │   └── websocket_manager.py      # Real-time messaging
  └── auth/
      └── auth_service.py           # Token verification

backend/src/web_ui/agent/
  ├── document_editor.py            # DocumentEditingAgent implementation
  └── orchestrator/
      ├── simple_orchestrator.py    # Task orchestration & streaming
      └── ...                       # Additional orchestration logic
```

* The **registry index** `/.well-known/agents.json` advertises your agent set and links to individual **agent cards** in `/.well-known/agents/*.json`.
* The backend exposes routes to **list agents, submit tasks, check progress**, and **chat** with an agent through a structured API.

---

## Agent discovery (public)

### Registry index

`/.well-known/agents.json` is the entry point that lists your agents and links to their cards:

```jsonc
{
  "registry_version": "1.0.0",
  "protocol_version": "a2a-v1",
  "organization": {
    "name": "web-ui",
    "contact": "simpleflowworks@gmail.com",
    "website": "https://github.com/savagelysubtle/web-ui"
  },
  "agents": [
    { "card_url": ".well-known/agents/document_editor.json" },
    { "card_url": ".well-known/agents/browser_use.json" },
    { "card_url": ".well-known/agents/deep_research.json" }
  ]
}
```

This placement under `/.well-known/` follows IETF guidance so clients know where to look. ([RFC Editor][1])

### Agent cards

Each card advertises a single agent's **name, description, endpoint, protocols, skills/capabilities,** and other metadata. Examples from your repo:

* `/.well-known/agents/browser_use.json`
  Key ideas in the card:

  * `agent_id`: `browser_use_agent`
  * `endpoint`: `https://…/a2a/agents/browser_use`
  * **Skills** like `browse` (navigate to URL & interact), plus typical web-automation capabilities.

* `/.well-known/agents/deep_research.json`
  Key ideas in the card:

  * `agent_id`: `deep_research_agent`
  * Endpoint under `/a2a/agents/deep_research`
  * Focus on multi-source research, verification, citations; uses long-running/stateful flows (fits LangGraph well). ([LangChain Docs][2])

* `/.well-known/agents/document_editor.json`
  Key ideas in the card:

  * `agent_id`: `document_editor_agent`
  * `endpoint`: `https://…/a2a/agents/document_editor`
  * **Core implementation**: `DocumentEditingAgent` class in `backend/src/web_ui/agent/document_editor.py`
  * **Skills** such as `create_document`, `edit_document`, file management with MCP tool integration
  * **Working directory**: `./tmp/documents` (configurable)
  * **LLM Integration**: Supports multiple providers (Ollama, Google, OpenAI) with configurable models

> These JSON cards are what UI clients and other services will fetch at runtime to learn what an agent can do and how to call it.

---

## Backend API Implementation

### FastAPI Application Structure

The main FastAPI application is defined in `backend/src/web_ui/api/server.py` with:

#### Lifespan Management
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize WebSocket manager, orchestrator, and document agent
    # Shutdown: Graceful cleanup of all services
```

#### Service Initialization
- **WebSocket Manager**: Global instance for real-time communication
- **Agent Orchestrator**: `SimpleAgentOrchestrator` for task coordination
- **Document Agent**: `DocumentEditingAgent` with configurable LLM provider

#### Environment Configuration
```python
llm_provider_name = os.getenv("LLM_PROVIDER", "ollama")
llm_model_name = os.getenv("LLM_MODEL", "llama3.2")
llm_temperature = float(os.getenv("LLM_TEMPERATURE", "0.3"))
llm_api_key = os.getenv("GOOGLE_API_KEY")
llm_base_url = os.getenv("LLM_BASE_URL")
```

### API Routes (private to your app)

Your FastAPI router in `backend/src/web_ui/api/routes/agents.py` exposes:

```
GET    /api/agents/available          # list agents & capabilities
POST   /api/agents/execute            # submit a task to an agent
GET    /api/agents/tasks              # list recent tasks
GET    /api/agents/tasks/{task_id}    # task status/result
DELETE /api/agents/tasks/{task_id}    # cancel (if supported)
GET    /api/agents/stats              # basic health/metrics
GET    /api/agents/health             # liveness/health check
GET    /api/agents/hello              # simple sanity endpoint
POST   /api/agents/chat               # chat with an agent (streaming)
POST   /api/agents/dev-login          # dev-only auth helper
```

### Additional API Modules

#### Authentication (`/api/auth`)
- Token-based authentication
- WebSocket authentication support
- Development login helpers

#### Documents (`/api/documents`)
- Document CRUD operations
- File upload/download
- Integration with DocumentEditingAgent

#### Real-time Communication
- **WebSocket endpoint**: `/ws` with token-based auth
- **WebSocket Manager**: Handles user connections, message routing
- **Event streaming**: Real-time task updates and agent communication

#### Integration Routes
- **AG-UI** (`/api/ag_ui`): Integration with AG-UI framework
- **CopilotKit** (`/api/copilotkit`): CopilotKit integration endpoints
- **Development** (`/api`): Development utilities and debugging

### Request/response models

* **Task submission** (simplified):

```jsonc
POST /api/agents/execute
{
  "agent_type": "browser_use" | "deep_research" | "document_editor",
  "action": "browse" | "create_document" | "...",
  "payload": { /* action-specific parameters */ }
}
```

Response:

```jsonc
{ "task_id": "uuid" }
```

* **Task status** (example shape):

```jsonc
GET /api/agents/tasks/{task_id}
{
  "id": "uuid",
  "agent_type": "document_editor",
  "action": "create_document",
  "status": "pending" | "running" | "completed" | "failed",
  "created_at": "...",
  "started_at": "...",
  "completed_at": "...",
  "result": { /* present on completed */ },
  "error": "..." /* present on failed */,
  "progress": { /* optional */ }
}
```

* **Chat** (synchronous/streamed by orchestrator):

```jsonc
POST /api/agents/chat
{
  "message": "Rewrite this doc in bullet points",
  "agent_type": "document_editor",
  "context_document_id": "optional"
}
```

### Agent Implementation Details

#### DocumentEditingAgent
Located in `backend/src/web_ui/agent/document_editor.py`:

- **MCP Tool Integration**: Extensible tool system for file operations
- **Multi-LLM Support**: Configurable provider system (Ollama, Google, OpenAI)
- **Working Directory**: Isolated document workspace
- **Async Operations**: Full async/await support for scalability

#### Orchestrator System
Located in `backend/src/web_ui/agent/orchestrator/`:

- **Task Management**: Queue and execute agent tasks
- **Event Streaming**: Real-time updates via WebSocket
- **Agent Registration**: Dynamic agent discovery and routing
- **State Management**: Track task progress and results

### Error Handling & Middleware

#### Global Error Handling (`middleware/error_handler.py`)
- **AppException**: Custom application exceptions
- **Validation errors**: Request validation with detailed messages
- **HTTP exceptions**: Proper status codes and responses
- **Generic exceptions**: Fallback error handling with logging

#### CORS Configuration
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## End-to-end flow

1. **Discover** agents by fetching `/.well-known/agents.json` and then individual cards. ([RFC Editor][1])
2. **List** available agents and actions via `GET /api/agents/available`.
3. **Submit** a task with `POST /api/agents/execute` (or use `POST /api/agents/chat` for conversational actions).
4. **Monitor** task progress via WebSocket connection at `/ws` or poll with `GET /api/agents/tasks/{task_id}`.
5. **Consume result** when `status` becomes `completed`.

---

## Adding a new agent

### 1. Create an agent card
Add `/.well-known/agents/<your_agent>.json` describing:

* `name`, `description`, `version`, `agent_id`
* `endpoint` (where this agent can be invoked)
* `protocols` (e.g., `a2a-v1`)
* `skills` (each with `name`, `description`, and `input_schema` if you validate inputs)
* Any extra metadata (capabilities, limitations, docs links)

Then reference it from `/.well-known/agents.json` by adding a new `{"card_url": ".well-known/agents/<your_agent>.json"}` entry.

### 2. Implement the agent class
Create your agent in `backend/src/web_ui/agent/` following the pattern of `DocumentEditingAgent`:

```python
class YourAgent:
    def __init__(self, **config):
        # Initialize with configuration
        pass

    async def initialize(self):
        # Async initialization
        pass

    async def execute_action(self, action: str, payload: dict):
        # Handle agent actions
        pass

    async def close(self):
        # Cleanup resources
        pass
```

### 3. Register in the application
In `backend/src/web_ui/api/server.py`:

```python
# Add to lifespan function
your_agent = YourAgent(**config)
await your_agent.initialize()
if orchestrator:
    orchestrator.register_agent("your_agent", your_agent)
```

### 4. Update routes
Extend `backend/src/web_ui/api/routes/agents.py` to handle your agent's specific actions and capabilities.

### 5. Add dependency injection
Update `backend/src/web_ui/api/dependencies.py` if your agent needs special dependency handling.

---

## Security & environment

* A development-only `POST /api/agents/dev-login` exists; disable it in production and use your standard auth.
* **WebSocket Authentication**: Token-based auth for real-time connections
* **Environment Variables**: Secure configuration for LLM providers and API keys
* Keep agent cards public, but **don't leak secrets** in them; they're meant for discovery, not credentials.
* Validate `payload` per action using a JSON Schema (`input_schema`) and enforce it server-side.

---

## Development & Testing

### Local Development
```bash
# Start the FastAPI server
cd backend
python -m web_ui.api.server

# Server runs on http://127.0.0.1:8000
# API docs available at http://127.0.0.1:8000/docs
```

### Health Checks
- **Application health**: `GET /health`
- **Agent status**: `GET /api/agents/health`
- **System info**: `GET /api/agents/stats`

### Logging
- **Frontend logging**: `POST /api/logs` for client-side error reporting
- **Server logging**: Configured via `web_ui.utils.logging_config`
- **Development routes**: Additional debugging endpoints under `/api`

---

## FAQ

**Why use `/.well-known` for agent cards?**
It's an IETF-standardized convention so clients know exactly where to look; you avoid hard-coding app-specific paths. ([RFC Editor][1])

**How should I model long-running research?**
Wrap it in a LangGraph graph (Python/JS) and expose a handler that integrates with your orchestrator's task lifecycle. ([LangChain Docs][2])

**Is this compatible with broader agent standards?**
Yes—agent cards + predictable discovery + typed inputs map nicely onto modern agent protocols (e.g., MCP) that connect apps to tools/data through standard interfaces. ([Model Context Protocol][3])

**How do I add WebSocket support for my agent?**
The `WebSocketManager` in `backend/src/web_ui/api/websocket/websocket_manager.py` handles connections. Register event handlers in your orchestrator to stream updates.

**Can I use different LLM providers?**
Yes, the `DocumentEditingAgent` supports multiple providers via environment variables. Add new providers by extending the LLM configuration system.

---

## Changelog

* **v1.1** — Added detailed API folder structure, implementation specifics, WebSocket details, and comprehensive development guide.
* **v1.0** — Initial doc: registry + cards under `/.well-known`, agent API routes, orchestrator notes, and contribution guide.

---

[1]: https://www.rfc-editor.org/info/rfc8615?utm_source=chatgpt.com "Information on RFC 8615"
[2]: https://docs.langchain.com/oss/python/langgraph/overview?utm_source=chatgpt.com "Overview - Docs by LangChain"
[3]: https://modelcontextprotocol.io/?utm_source=chatgpt.com "Model Context Protocol"
