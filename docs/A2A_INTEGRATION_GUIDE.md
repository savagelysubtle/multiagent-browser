# Agent-to-Agent (A2A) Protocol Integration Guide

## Overview

All agents in the web-ui project now support the Google Agent-to-Agent (A2A) protocol concepts, enabling seamless inter-agent communication, collaboration, and task delegation through the `SimpleAgentOrchestrator`.

> **⚠️ Important**: This is a **preparation implementation** (v0.1.0) that establishes agent-to-agent communication patterns aligned with A2A principles. The current implementation uses **internal Python message passing** for local agents. Full A2A protocol compliance (JSON-RPC 2.0 over HTTP(S), Agent Cards, etc.) is planned for future releases. See **[A2A_PROTOCOL_COMPLIANCE.md](A2A_PROTOCOL_COMPLIANCE.md)** for detailed compliance analysis and roadmap.
>
> **What this means**:
> - ✅ Agents can communicate and collaborate (works today)
> - ✅ Core A2A patterns and concepts implemented
> - ⏳ HTTP(S) transport and JSON-RPC format (planned)
> - ⏳ Standardized Agent Cards (planned)
> - ⏳ External agent federation (planned)

## A2A-Enabled Agents

### 1. Browser Use Agent (`BrowserUseAdapter`)
- **Agent ID**: `browser_use_agent`
- **Capabilities**: Web browsing, data extraction, screenshots
- **A2A Actions**:
  - `browse`: Navigate and interact with web pages
  - `extract`: Extract data using CSS selectors
  - `screenshot`: Capture webpage screenshots

### 2. Deep Research Agent (`DeepResearchAdapter`)
- **Agent ID**: `deep_research_agent`
- **Capabilities**: Multi-source research, source analysis
- **A2A Actions**:
  - `research`: Conduct comprehensive research on topics
  - `analyze_sources`: Evaluate source credibility and relevance
- **Collaboration**: Can provide research assistance to other agents

### 3. Document Editor Agent (`DocumentEditorAdapter`)
- **Agent ID**: `document_editor_agent`
- **Capabilities**: Document CRUD, AI-powered editing, search
- **A2A Actions**:
  - `create_document`: Create new documents
  - `edit_document`: AI-assisted document editing
  - `search_documents`: Search document database
  - `chat`: Conversational interaction
- **Collaboration**: Can save research results and provide document assistance

## A2A Message Types

### Standard Message Types
1. **task_request**: Request an agent to perform an action
2. **capability_query**: Query agent capabilities
3. **status_query**: Check agent status
4. **collaboration_request**: Request agent collaboration
5. **document_query**: Document-specific queries (Document Editor only)

### Message Structure
```python
from backend.src.web_ui.agent.orchestrator.simple_orchestrator import A2AMessage

message = A2AMessage(
    id="unique_message_id",
    sender_agent="browser_use_agent",
    recipient_agent="document_editor_agent",
    message_type="collaboration_request",
    payload={
        "type": "save_research",
        "filename": "research_results.md",
        "content": "Research findings..."
    },
    conversation_id="conv_123",
    timestamp=datetime.utcnow(),
    metadata={"priority": "high"}
)
```

## Usage Examples

### Example 1: Browser Agent → Document Editor Collaboration

```python
from backend.src.web_ui.agent import initialize_orchestrator
from backend.src.web_ui.agent.adapters import (
    BrowserUseAdapter,
    DocumentEditorAdapter
)

# Initialize orchestrator with WebSocket manager
orchestrator = initialize_orchestrator(ws_manager)

# Register agents
browser_adapter = BrowserUseAdapter()
doc_adapter = DocumentEditorAdapter()

orchestrator.register_agent("browser_use", browser_adapter)
orchestrator.register_agent("document_editor", doc_adapter)

# Browser agent performs research
browser_result = await browser_adapter.browse(
    url="https://example.com",
    instruction="Research AI trends"
)

# Browser agent requests Document Editor to save results
await orchestrator.request_agent_collaboration(
    requesting_agent="browser_use",
    target_agent="document_editor",
    collaboration_type="save_research",
    payload={
        "filename": "ai_trends_research.md",
        "content": browser_result["result"]["content"]
    }
)
```

### Example 2: Research Agent → Browser Agent Collaboration

```python
# Research agent requests browser assistance
await orchestrator.request_agent_collaboration(
    requesting_agent="deep_research",
    target_agent="browser_use",
    collaboration_type="research_assistance",
    payload={
        "topic": "Quantum Computing Applications",
        "sources": ["https://arxiv.org", "https://nature.com"]
    }
)
```

### Example 3: Direct A2A Message

```python
# Send A2A message between agents
message = await orchestrator.send_a2a_message(
    sender_agent="document_editor",
    recipient_agent="deep_research",
    message_type="task_request",
    payload={
        "action": "research",
        "params": {
            "topic": "LangChain best practices",
            "depth": "comprehensive"
        }
    }
)
```

### Example 4: Broadcast Message to All Agents

```python
# Broadcast status update to all agents
result = await orchestrator.broadcast_message(
    sender_agent="orchestrator",
    message_type="status_query",
    payload={"timestamp": datetime.utcnow().isoformat()}
)

print(f"Successful: {result['successful']}")
print(f"Failed: {result['failed']}")
```

### Example 5: Query Agent Capabilities

```python
# Query specific agent capabilities
capabilities = await orchestrator.query_agent_capabilities("browser_use")

if capabilities["success"]:
    print(f"Browser Agent Capabilities: {capabilities['capabilities']}")
```

### Example 6: Check Agent Status

```python
# Get agent status
status = orchestrator.get_agent_status("document_editor")

print(f"Registered: {status['registered']}")
print(f"A2A Enabled: {status['a2a_enabled']}")
print(f"Capabilities: {status['capabilities']}")
```

## Agent Collaboration Patterns

### Pattern 1: Research → Document Creation
```python
# 1. Deep Research Agent conducts research
research_result = await deep_research_adapter.research(
    topic="Machine Learning Trends 2025",
    depth="comprehensive"
)

# 2. Research Agent requests Document Editor to save results
await orchestrator.send_a2a_message(
    sender_agent="deep_research",
    recipient_agent="document_editor",
    message_type="collaboration_request",
    payload={
        "type": "save_research",
        "filename": "ml_trends_2025.md",
        "content": research_result["summary"]
    }
)
```

### Pattern 2: Browse → Research → Document
```python
# 1. Browser Agent gathers initial data
browser_data = await browser_adapter.browse(
    url="https://research-site.com",
    instruction="Collect recent studies on topic X"
)

# 2. Deep Research Agent analyzes sources
await orchestrator.send_a2a_message(
    sender_agent="browser_use",
    recipient_agent="deep_research",
    message_type="task_request",
    payload={
        "action": "analyze_sources",
        "params": {
            "sources": browser_data["result"]["sources"]
        }
    }
)

# 3. Document Editor creates final report
# (triggered by deep_research completion event)
```

### Pattern 3: Document Query → Research Enhancement
```python
# 1. Document Editor identifies knowledge gap
doc_query = await doc_adapter.search_documents(
    query="neural architecture search"
)

# 2. If insufficient results, request research assistance
if len(doc_query) < 3:
    await orchestrator.request_agent_collaboration(
        requesting_agent="document_editor",
        target_agent="deep_research",
        collaboration_type="research_assistance",
        payload={
            "topic": "neural architecture search",
            "context": "Expanding knowledge base"
        }
    )
```

## Conversation Tracking

### Track A2A Conversations
```python
import uuid

# Create conversation ID
conversation_id = str(uuid.uuid4())

# Send multiple messages in same conversation
msg1 = await orchestrator.send_a2a_message(
    sender_agent="browser_use",
    recipient_agent="document_editor",
    message_type="task_request",
    payload={"action": "create_document", "params": {...}},
    conversation_id=conversation_id
)

msg2 = await orchestrator.send_a2a_message(
    sender_agent="document_editor",
    recipient_agent="browser_use",
    message_type="response",
    payload={"status": "completed", "document_id": "doc_123"},
    conversation_id=conversation_id
)

# Retrieve conversation history
conversation = orchestrator.get_a2a_conversation(conversation_id)
print(f"Messages in conversation: {len(conversation)}")
```

## Best Practices

### 1. Always Include Conversation ID
```python
# Good: Trackable conversation
conversation_id = str(uuid.uuid4())
await orchestrator.send_a2a_message(
    ...,
    conversation_id=conversation_id
)
```

### 2. Handle A2A Response Errors
```python
result = await orchestrator.request_agent_collaboration(...)
if not result["success"]:
    logger.error(f"Collaboration failed: {result['error']}")
    # Implement fallback logic
```

### 3. Use Specific Message Types
```python
# Good: Specific message type
message_type = "collaboration_request"

# Bad: Generic message type
message_type = "request"  # Too vague
```

### 4. Validate Payloads
```python
# Ensure required fields are present
payload = {
    "action": "research",
    "params": {
        "topic": topic,  # Required
        "depth": "standard"  # Default provided
    }
}
```

## Integration with Google A2A Interface

The adapters work seamlessly with the `GoogleA2AInterface`:

```python
from backend.src.web_ui.agent.google_a2a.interface import (
    initialize_a2a_interface,
    A2AMessageType
)

# Initialize Google A2A interface
a2a_interface = initialize_a2a_interface(orchestrator)

# Adapters automatically register with A2A interface
# Enable A2A when Google's protocol becomes available
a2a_interface.enable_a2a()
```

## Testing A2A Integration

```python
# Test agent registration
status = orchestrator.get_agent_status("browser_use")
assert status["a2a_enabled"] == True
assert status["has_handle_a2a"] == True

# Test message delivery
message = await orchestrator.send_a2a_message(
    sender_agent="test_agent",
    recipient_agent="browser_use",
    message_type="capability_query",
    payload={}
)
assert message.id is not None

# Test collaboration
result = await orchestrator.request_agent_collaboration(
    requesting_agent="document_editor",
    target_agent="deep_research",
    collaboration_type="research_assistance",
    payload={"topic": "test topic"}
)
assert result["success"] == True
```

## Troubleshooting

### Agent Not Receiving A2A Messages
1. Check agent registration: `orchestrator.get_agent_status(agent_type)`
2. Verify `handle_a2a_message` method exists
3. Check A2A message type is supported by agent

### Collaboration Request Fails
1. Verify target agent supports the collaboration type
2. Check payload contains required fields
3. Review agent logs for error messages

### Message Not Found in Conversation
1. Ensure same `conversation_id` is used for all related messages
2. Check message was successfully sent (no exceptions)
3. Verify conversation ID in message payload

## Future Enhancements

1. **External A2A Endpoints**: Support for agents on different servers
2. **Message Queuing**: Persistent message queue for offline agents
3. **Protocol Extensions**: Additional message types for specialized workflows
4. **Security**: Authentication and authorization for A2A communications
5. **Monitoring**: A2A message analytics and performance tracking

## Summary

All agents in the web-ui project are now A2A-compatible and can:
- Communicate directly via the orchestrator
- Collaborate on complex tasks
- Share data and results seamlessly
- Query each other's capabilities
- Track conversations across multiple interactions

This integration creates a powerful multi-agent system where specialized agents work together to accomplish complex research and document management tasks.
