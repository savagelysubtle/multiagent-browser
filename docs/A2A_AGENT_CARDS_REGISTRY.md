# A2A Agent Cards Registry

## Overview

This document provides the connection between the A2A implementation documentation and the standardized Agent Cards available in the `.well-known` directory.

## Agent Card Locations

### Standard A2A Location (`.well-known/`)

Following the A2A protocol specification, all agent cards are published in the `.well-known` directory at the project root:

```
.well-known/
├── agents.json                     # Main agent registry
└── agents/
    ├── document_editor.json        # Document Editor Agent Card
    ├── browser_use.json            # Browser Use Agent Card
    └── deep_research.json          # Deep Research Agent Card
```

### Documentation Location (`backend/src/web_ui/agent/`)

Human-readable documentation and implementation details:

- `A2A_AGENT_CARDS.md` - Visual reference guide with examples
- `A2A_IMPLEMENTATION_SUMMARY.md` - Technical implementation details
- `A2A_INTEGRATION_GUIDE.md` - Integration instructions and usage
- `A2A_PROTOCOL_COMPLIANCE.md` - Compliance roadmap

## Quick Links

### Agent Registry
- **Main Registry**: [.well-known/agents.json](../../.well-known/agents.json)
- **Registry README**: [.well-known/README.md](../../.well-known/README.md)

### Individual Agent Cards
- **Document Editor**: [.well-known/agents/document_editor.json](../../.well-known/agents/document_editor.json)
- **Browser Use**: [.well-known/agents/browser_use.json](../../.well-known/agents/browser_use.json)
- **Deep Research**: [.well-known/agents/deep_research.json](../../.well-known/agents/deep_research.json)

## Agent Card Format

Each agent card follows the A2A protocol specification:

```json
{
  "name": "Agent Name",
  "description": "Agent description",
  "version": "1.0.0",
  "agent_id": "unique_agent_id",
  "endpoint": "https://domain.com/a2a/agents/agent_id",
  "protocols": ["a2a-v1"],
  "skills": [
    {
      "name": "skill_name",
      "description": "Skill description",
      "input_schema": { /* JSON Schema */ },
      "output_schema": { /* JSON Schema */ }
    }
  ],
  "supported_modalities": ["text", "files"],
  "collaboration_patterns": [
    {
      "name": "pattern_name",
      "description": "Pattern description",
      "input_format": "structured"
    }
  ],
  "metadata": { /* Agent-specific metadata */ }
}
```

## Accessing Agent Cards

### Via File System
```bash
# View main registry
cat .well-known/agents.json

# View specific agent card
cat .well-known/agents/document_editor.json
```

### Via HTTP (Future)
Once HTTP transport is implemented:

```bash
# Get agent registry
curl https://webui.example.com/.well-known/agents.json

# Get specific agent card
curl https://webui.example.com/.well-known/agents/document_editor.json
```

### Via Python API
```python
import json
from pathlib import Path

# Load agent registry
registry_path = Path(".well-known/agents.json")
with open(registry_path) as f:
    registry = json.load(f)

# Load specific agent card
agent_card_path = Path(".well-known/agents/document_editor.json")
with open(agent_card_path) as f:
    agent_card = json.load(f)

# Access agent skills
for skill in agent_card["skills"]:
    print(f"Skill: {skill['name']}")
    print(f"Description: {skill['description']}")
```

## Agent Summary

### Document Editor Agent
- **Agent ID**: `document_editor_agent`
- **Skills**: 4 (create_document, edit_document, search_documents, chat)
- **Collaboration Patterns**: 2 (save_research, document_assistance)
- **Message Types**: 5 (task_request, capability_query, status_query, document_query, collaboration_request)

### Browser Use Agent
- **Agent ID**: `browser_use_agent`
- **Skills**: 3 (browse, extract, screenshot)
- **Collaboration Patterns**: 1 (web_data_gathering)
- **Message Types**: 3 (task_request, capability_query, status_query)

### Deep Research Agent
- **Agent ID**: `deep_research_agent`
- **Skills**: 2 (research, analyze_sources)
- **Collaboration Patterns**: 1 (research_assistance)
- **Message Types**: 4 (task_request, capability_query, status_query, collaboration_request)

## Integration with Orchestrator

The SimpleAgentOrchestrator uses the agent capabilities defined in these cards:

```python
from backend.src.web_ui.agent import initialize_orchestrator

# Initialize with WebSocket manager
orchestrator = initialize_orchestrator(ws_manager)

# Get available agents (includes A2A metadata)
agents = orchestrator.get_available_agents()

# Agent cards align with orchestrator capabilities
for agent in agents:
    if agent.get("a2a_enabled"):
        print(f"A2A Agent: {agent['name']}")
        print(f"Agent ID: {agent['agent_id']}")
        print(f"Skills: {[action['name'] for action in agent['actions']]}")
```

## Updating Agent Cards

When modifying agent capabilities:

1. **Update Adapter Code**: Modify the agent adapter in `backend/src/web_ui/agent/adapters/`
2. **Update Agent Card**: Modify the JSON file in `.well-known/agents/`
3. **Update Registry**: Update `.well-known/agents.json` if metadata changed
4. **Update Documentation**: Update `A2A_AGENT_CARDS.md` with visual examples
5. **Test Integration**: Verify orchestrator detects changes correctly

## Version Alignment

All components maintain version synchronization:

| Component | Version | Status |
|-----------|---------|--------|
| A2A Implementation | 0.1.0 | Preparation |
| Agent Cards | 1.0.0 | Active |
| Protocol Support | a2a-v1 | Preparation |
| Orchestrator | - | Active |

## Compliance Status

**Current**: Preparation Implementation (v0.1.0)
- ✅ Agent Cards created with proper schema
- ✅ Registry established in `.well-known`
- ✅ Skills documented with input/output schemas
- ✅ Collaboration patterns defined
- ⏳ HTTP transport (planned)
- ⏳ JSON-RPC 2.0 format (planned)

See [A2A_PROTOCOL_COMPLIANCE.md](A2A_PROTOCOL_COMPLIANCE.md) for the full compliance roadmap.

## References

### A2A Documentation
- [Agent Cards (Visual)](A2A_AGENT_CARDS.md)
- [Implementation Summary](A2A_IMPLEMENTATION_SUMMARY.md)
- [Integration Guide](A2A_INTEGRATION_GUIDE.md)
- [Protocol Compliance](A2A_PROTOCOL_COMPLIANCE.md)

### Agent Cards Directory
- [Registry README](../../.well-known/README.md)
- [Main Registry](../../.well-known/agents.json)
- [Agents Directory](../../.well-known/agents/)

### Official A2A Resources
- [A2A Protocol Specification](https://a2a-protocol.org/)
- [Agent Card Specification](https://a2a-protocol.org/latest/topics/agent-cards/)
- [A2A and MCP Relationship](https://a2a-protocol.org/latest/topics/a2a-and-mcp/)

---

  **Last Updated**: 2025-10-01
  **Implementation Version**: 0.1.0
  **Status**: ✅ Agent Cards Published
