# Agent Cards - A2A Protocol

This directory contains Agent Cards following the Google Agent-to-Agent (A2A) protocol specification. Agent Cards provide standardized descriptions of agent capabilities, skills, and collaboration patterns.

## Overview

The web-ui project implements **3 A2A-enabled agents**:

1. **Document Editor Agent** - AI-powered document creation and editing
2. **Browser Use Agent** - Web browsing and data extraction
3. **Deep Research Agent** - Comprehensive multi-source research

## Directory Structure

```
.well-known/
├── README.md                       # This file
├── agents.json                     # Main agent registry/index
└── agents/
    ├── document_editor.json        # Document Editor Agent Card
    ├── browser_use.json            # Browser Use Agent Card
    └── deep_research.json          # Deep Research Agent Card
```

## Agent Registry

The main entry point is `agents.json`, which provides:
- List of all available agents
- Quick summary of capabilities
- Links to detailed agent cards
- Implementation status and roadmap

## Agent Cards

Each agent has a detailed card in the `agents/` directory containing:

- **Agent Metadata**: ID, name, version, endpoint
- **Skills**: Detailed input/output schemas for each capability
- **Collaboration Patterns**: How the agent works with other agents
- **Supported Modalities**: Text, files, images, etc.
- **Metadata**: Technical details, limitations, and features

## A2A Protocol Compliance

**Current Status**: Preparation Implementation (v0.1.0)

This implementation establishes the foundation for A2A protocol but currently uses **internal Python message passing** rather than the official JSON-RPC 2.0 over HTTP(S) transport.

### What Works Today
✅ Agent-to-agent communication
✅ Capability discovery
✅ Collaboration patterns
✅ Message routing
✅ Conversation tracking

### Planned for Full Compliance
⏳ JSON-RPC 2.0 message format
⏳ HTTP(S) transport layer
⏳ Standardized Agent Card format (in progress)
⏳ Task lifecycle management
⏳ Multi-modal data support
⏳ Security and authentication

See [A2A_PROTOCOL_COMPLIANCE.md](../backend/src/web_ui/agent/A2A_PROTOCOL_COMPLIANCE.md) for the complete roadmap.

## Usage Examples

### Discovering Available Agents

```bash
# Get agent registry
curl https://webui.example.com/.well-known/agents.json

# Get specific agent card
curl https://webui.example.com/.well-known/agents/document_editor.json
```

### Skill Invocation (Future)

Once HTTP transport is implemented:

```bash
# Create a document via A2A
curl -X POST https://webui.example.com/a2a/agents/document_editor \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "execute_skill",
    "params": {
      "skill_name": "create_document",
      "arguments": {
        "filename": "research.md",
        "content": "# Research Notes",
        "document_type": "markdown"
      }
    },
    "id": "request-123"
  }'
```

## Integration with Orchestrator

The SimpleAgentOrchestrator automatically detects and registers A2A-enabled agents:

```python
from backend.src.web_ui.agent import initialize_orchestrator
from backend.src.web_ui.agent.adapters import (
    DocumentEditorAdapter,
    BrowserUseAdapter,
    DeepResearchAdapter
)

# Initialize orchestrator
orchestrator = initialize_orchestrator(ws_manager)

# Register A2A-enabled agents
orchestrator.register_agent("document_editor", DocumentEditorAdapter())
orchestrator.register_agent("browser_use", BrowserUseAdapter())
orchestrator.register_agent("deep_research", DeepResearchAdapter())

# Get available agents with A2A metadata
agents = orchestrator.get_available_agents()
```

## Collaboration Patterns

### Pattern 1: Research → Document Storage
```
Deep Research Agent → Document Editor Agent
  Type: collaboration_request
  Pattern: save_research
  Result: Research findings saved as document
```

### Pattern 2: Document Query → Research Enhancement
```
Document Editor Agent → Deep Research Agent
  Type: collaboration_request
  Pattern: research_assistance
  Result: Knowledge base expanded with new research
```

### Pattern 3: Browser Data → Research Analysis
```
Deep Research Agent → Browser Use Agent
  Type: task_request
  Pattern: web_data_gathering
  Result: Web data collected and analyzed
```

## Schema Validation

All Agent Cards conform to JSON Schema for validation. The schemas include:

- **Input Schema**: Validates skill invocation parameters
- **Output Schema**: Defines expected response structure
- **Collaboration Schema**: Structures for inter-agent communication

## Documentation

For more detailed information, see:

- [A2A Agent Cards](../backend/src/web_ui/agent/A2A_AGENT_CARDS.md) - Visual reference
- [A2A Implementation Summary](../backend/src/web_ui/agent/A2A_IMPLEMENTATION_SUMMARY.md) - Technical details
- [A2A Integration Guide](../backend/src/web_ui/agent/A2A_INTEGRATION_GUIDE.md) - Usage examples
- [A2A Protocol Compliance](../backend/src/web_ui/agent/A2A_PROTOCOL_COMPLIANCE.md) - Compliance roadmap

## Contributing

When adding new agents:

1. Create agent card in `.well-known/agents/{agent_id}.json`
2. Follow the A2A Agent Card schema
3. Update `agents.json` registry
4. Implement `handle_a2a_message()` in agent adapter
5. Register agent with orchestrator
6. Update documentation

## Version History

- **v0.1.0** (2025-10-01): Initial preparation implementation
  - Created Agent Cards for 3 agents
  - Established directory structure
  - Documented current capabilities and roadmap

---

  **Implementation Status**: ✅ Preparation Ready
  **Next Phase**: Core Protocol Alignment (JSON-RPC 2.0)
  **Target Compliance**: Q2 2025
