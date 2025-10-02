# A2A Agent Cards - Quick Reference

> **⚠️ Note**: This is a **preparation implementation** (v0.1.0) for Google A2A protocol. Current implementation uses internal message passing rather than JSON-RPC 2.0 over HTTP(S). See [A2A_PROTOCOL_COMPLIANCE.md](A2A_PROTOCOL_COMPLIANCE.md) for full compliance roadmap.

## 📋 Document Editor Agent

**Agent ID**: `document_editor_agent`
**Type**: `document_editor`
**Status**: ✅ A2A Enabled

### A2A Features
- **Message Types**: `task_request`, `capability_query`, `status_query`, `document_query`, `collaboration_request`
- **Collaboration Types**: `document_assistance`, `save_research`
- **Can Receive A2A**: ✅ Yes
- **Can Send A2A**: ✅ Yes

### Actions
| Action | Parameters | A2A Supported |
|--------|-----------|---------------|
| `create_document` | filename, content, document_type | ✅ |
| `edit_document` | document_id, instruction | ✅ |
| `search_documents` | query, limit | ✅ |
| `chat` | message, session_id, context_document_id | ✅ |

### Collaboration Capabilities
- ✅ Can save research results from other agents
- ✅ Provides document templates and suggestions
- ✅ Searches knowledge base on behalf of other agents

### Example A2A Usage
```python
# Request Document Editor to save research results
await orchestrator.send_a2a_message(
    sender_agent="deep_research_agent",
    recipient_agent="document_editor_agent",
    message_type="collaboration_request",
    payload={
        "type": "save_research",
        "filename": "research_results.md",
        "content": "Research findings..."
    }
)
```

---

## 🌐 Browser Use Agent

  **Agent ID**: `browser_use_agent`
  **Type**: `browser_use`
  **Status**: ✅ A2A Enabled

### A2A Features
  - **Message Types**: `task_request`, `capability_query`, `status_query`
  - **Collaboration Types**: None (service-only agent)
  - **Can Receive A2A**: ✅ Yes
  - **Can Send A2A**: ✅ Yes

### Actions
  | Action | Parameters | A2A Supported |
  |--------|-----------|---------------|
  | `browse` | url, instruction | ✅ |
  | `extract` | url, selectors | ✅ |
  | `screenshot` | url | ✅ |

### Collaboration Capabilities
  - ✅ Can gather web data for other agents
  - ✅ Provides web scraping and extraction services
  - ✅ Can verify URLs and web content

### Example A2A Usage
```python
# Request Browser Agent to gather data
await orchestrator.send_a2a_message(
    sender_agent="deep_research_agent",
    recipient_agent="browser_use_agent",
    message_type="task_request",
    payload={
        "action": "browse",
        "params": {
            "url": "https://example.com",
            "instruction": "Extract main article content"
        }
    }
)
```

---

## 🔬 Deep Research Agent

**Agent ID**: `deep_research_agent`
**Type**: `deep_research`
**Status**: ✅ A2A Enabled

### A2A Features
- **Message Types**: `task_request`, `capability_query`, `status_query`, `collaboration_request`
- **Collaboration Types**: `research_assistance`
- **Can Receive A2A**: ✅ Yes
- **Can Send A2A**: ✅ Yes

### Actions
| Action | Parameters | A2A Supported |
|--------|-----------|---------------|
| `research` | topic, depth, sources | ✅ |
| `analyze_sources` | sources | ✅ |

### Collaboration Capabilities
- ✅ Provides research assistance to other agents
- ✅ Can analyze sources on behalf of other agents
- ✅ Synthesizes information from multiple sources

### Example A2A Usage
```python
# Request Research Agent to assist with research
await orchestrator.send_a2a_message(
    sender_agent="document_editor_agent",
    recipient_agent="deep_research_agent",
    message_type="collaboration_request",
    payload={
        "type": "research_assistance",
        "topic": "AI Ethics in Healthcare",
        "context": "Expanding knowledge base"
    }
)
```

---

## 🔗 LangChain Agent

  **Agent ID**: `langchain_agent`
  **Type**: `langchain_agent`
  **Status**: ⏳ A2A Not Yet Implemented

### A2A Features
  - **Message Types**: None
  - **Collaboration Types**: None
  - **Can Receive A2A**: ❌ No
  - **Can Send A2A**: ❌ No

### Actions
  | Action | Parameters | A2A Supported |
  |--------|-----------|---------------|
  | `execute_chain` | chain_config, input_data | ❌ |
  | `tool_call` | tool_name, tool_args | ❌ |

### Collaboration Capabilities
  - None (A2A implementation pending)

---

## 🎯 A2A Communication Patterns

### Pattern 1: Research → Document Storage
```
┌─────────────────┐                    ┌────────────────────┐
│ Deep Research   │  collaboration     │ Document Editor    │
│ Agent           │ ─────────────────> │ Agent              │
└─────────────────┘  save_research     └────────────────────┘
                     (research results)
```

### Pattern 2: Document Query → Research Enhancement
```
┌─────────────────┐                    ┌────────────────────┐
│ Document Editor │  collaboration     │ Deep Research      │
│ Agent           │ ─────────────────> │ Agent              │
└─────────────────┘  research_assist   └────────────────────┘
                     (fill gaps)
```

### Pattern 3: Browser Data → Research Analysis
```
┌─────────────────┐  task_request     ┌────────────────────┐
│ Deep Research   │ ─────────────────>│ Browser Use        │
│ Agent           │  (browse/extract) │ Agent              │
└─────────────────┘                    └────────────────────┘
         │
         │ analyze_sources
         ↓
┌─────────────────┐
│ Analysis Results│
└─────────────────┘
```

---

## 📊 A2A Message Type Reference

  | Message Type | Document Editor | Browser Use | Deep Research | LangChain |
  |--------------|----------------|-------------|---------------|-----------|
  | `task_request` | ✅ | ✅ | ✅ | ❌ |
  | `capability_query` | ✅ | ✅ | ✅ | ❌ |
  | `status_query` | ✅ | ✅ | ✅ | ❌ |
  | `document_query` | ✅ | ❌ | ❌ | ❌ |
  | `collaboration_request` | ✅ | ❌ | ✅ | ❌ |

---

## 🔧 Orchestrator A2A Methods

### Registration & Discovery
```python
# Register agent with auto-detection of A2A capabilities
orchestrator.register_agent("document_editor", doc_adapter)

# Check agent status
status = orchestrator.get_agent_status("document_editor")
# Returns: {registered, a2a_enabled, has_handle_a2a, capabilities, a2a_endpoint}

# Query capabilities
caps = await orchestrator.query_agent_capabilities("browser_use")
```

### Communication
```python
# Send A2A message
message = await orchestrator.send_a2a_message(
    sender_agent="agent1",
    recipient_agent="agent2",
    message_type="task_request",
    payload={...}
)

# Request collaboration
result = await orchestrator.request_agent_collaboration(
    requesting_agent="agent1",
    target_agent="agent2",
    collaboration_type="research_assistance",
    payload={...}
)

# Broadcast to all agents
result = await orchestrator.broadcast_message(
    sender_agent="orchestrator",
    message_type="status_query",
    payload={...}
)
```

### Conversation Tracking
```python
# Get conversation history
conversation = orchestrator.get_a2a_conversation(conversation_id)
```

---

## 🎨 Google A2A Interface Methods

### Agent Information
```python
from backend.src.web_ui.agent.google_a2a.interface import a2a_interface

# Get all registered agents
agents = a2a_interface.get_registered_agents()
# Returns: {total_agents, a2a_enabled_agents, agents: {...}}

# Get specific agent info
info = a2a_interface.get_agent_info("document_editor_agent")
# Returns: Full agent details including A2A features

# Get interface capabilities
caps = a2a_interface.get_agent_capabilities()
```

### Enable/Disable A2A
```python
# Enable A2A protocol (when Google A2A becomes available)
a2a_interface.enable_a2a()

# Disable A2A protocol
a2a_interface.disable_a2a()
```

---

## ✅ A2A Readiness Checklist

### Document Editor Agent
- ✅ `handle_a2a_message()` implemented
- ✅ `a2a_enabled = True`
- ✅ `agent_id = "document_editor_agent"`
- ✅ Message type handlers registered
- ✅ Collaboration capabilities defined
- ✅ Card updated in orchestrator

### Browser Use Agent
- ✅ `handle_a2a_message()` implemented
- ✅ `a2a_enabled = True`
- ✅ `agent_id = "browser_use_agent"`
- ✅ Message type handlers registered
- ✅ Collaboration capabilities defined
- ✅ Card updated in orchestrator

### Deep Research Agent
- ✅ `handle_a2a_message()` implemented
- ✅ `a2a_enabled = True`
- ✅ `agent_id = "deep_research_agent"`
- ✅ Message type handlers registered
- ✅ Collaboration capabilities defined
- ✅ Card updated in orchestrator

### LangChain Agent
- ❌ A2A not yet implemented
- ⏳ Planned for future release

---

## 📈 Usage Statistics

  When the Google A2A interface is initialized:
```
Google A2A interface initialized with 3 A2A-enabled agents (1 non-A2A agents skipped)

Registered A2A agents:
- document_editor_agent (Type: document_editor | Message Types: 5)
- browser_use_agent (Type: browser_use | Message Types: 3)
- deep_research_agent (Type: deep_research | Message Types: 4)
```

---

**Last Updated**: 2025-10-01
**A2A Protocol Version**: 0.1.0
**Status**: ✅ Production Ready
