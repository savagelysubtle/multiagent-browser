# MCP Configuration Storage in ChromaDB

## 🎯 **Objective**
Create a specialized database storage system for MCP (Model Context Protocol) configurations using ChromaDB, enabling persistent storage, automatic startup retrieval, and version management of MCP server configurations.

## 🏗️ **Architecture Overview**

### Current MCP Flow (Before)
```
User uploads mcp.json → UI Settings Text → Temporary Storage → Lost on restart
```

### Enhanced MCP Flow (After)
```
User uploads mcp.json → ChromaDB Collection → Persistent Storage → Auto-retrieval on startup
```

## 📊 **Database Design**

### New ChromaDB Collection: `mcp_configurations`

**Purpose**: Store MCP server configurations with metadata and versioning

**Schema**:
```python
{
    "id": "mcp_config_primary" | "mcp_config_backup_v2" | "mcp_config_custom_name",
    "content": "{\"mcpServers\": {...}}",  # Full MCP JSON config
    "metadata": {
        "config_name": "Primary Configuration",
        "config_type": "primary" | "backup" | "custom",
        "version": "1.0.0",
        "created_at": "2025-09-27T13:30:00Z",
        "last_used": "2025-09-27T14:15:00Z",
        "server_count": 3,
        "servers": ["unified-mcp-server", "filesystem-server", "brave-search"],
        "is_active": true,
        "description": "Main MCP configuration with filesystem and search tools",
        "upload_source": "file_upload" | "manual_entry" | "auto_generated"
    }
}
```

## 🔧 **Implementation Plan**

### Phase 1: Database Layer Enhancement ✅
- [x] Create MCPConfigManager class
- [x] Add mcp_configurations collection
- [x] Implement basic store/retrieve functionality
- [x] Add startup configuration loading

### Phase 2: UI Enhancement 🔄
- [ ] Create MCP Manager tab
- [ ] Enhanced upload handling with database storage
- [ ] Configuration list and management interface
- [ ] Basic version control

### Phase 3: Advanced Features 📋
- [ ] Health monitoring and validation
- [ ] Configuration templates
- [ ] Auto-backup and rollback
- [ ] Error handling and recovery

### Phase 4: Polish & Documentation 📝
- [ ] Testing and bug fixes
- [ ] Performance optimization
- [ ] Documentation and examples
- [ ] Integration testing with various MCP servers

## 📂 **File Structure**
```
src/web_ui/database/
├── mcp_config_manager.py     # MCP configuration management
├── mcp_version_manager.py    # Version control for configs
└── mcp_health_monitor.py     # Health monitoring

src/web_ui/services/
└── mcp_service.py           # Background MCP service

src/web_ui/webui/components/
└── mcp_manager_tab.py       # UI for MCP management
```

## 🚀 **Usage**

### Storing Configuration
```python
mcp_manager = MCPConfigManager(document_pipeline)
await mcp_manager.store_mcp_config(
    config_data=config_data,
    config_name="development_environment",
    description="Dev setup with filesystem and search capabilities"
)
```

### Auto-retrieval at Startup
```python
webui_manager = WebuiManager()
await webui_manager.initialize_mcp_from_database()
```

This integration transforms MCP configuration from temporary UI state into a robust, persistent, versioned database-backed system! 🎯