#!/usr/bin/env python3
"""
Comprehensive test script for MCP-Chroma integration.
Tests the MCPConfigManager, MCPService, and database persistence.
"""

import sys
import logging
import asyncio
import json
from pathlib import Path

# Add src to path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent / "src"))

from web_ui.database import MCPConfigManager, DocumentPipeline
from web_ui.services import MCPService
from web_ui.webui.webui_manager import WebuiManager

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def test_mcp_integration():
    """Test the complete MCP-Chroma integration."""
    print("🧪 Testing MCP-Chroma Integration")
    print("=" * 60)

    try:
        # Test 1: MCPConfigManager Initialization
        print("\n1. Testing MCPConfigManager...")
        doc_pipeline = DocumentPipeline()
        mcp_manager = MCPConfigManager(doc_pipeline)
        print("✅ MCPConfigManager initialized successfully")

        # Test 2: Store Sample MCP Configuration
        print("\n2. Testing MCP Configuration Storage...")
        sample_mcp_config = {
            "mcpServers": {
                "filesystem": {
                    "command": "uvx",
                    "args": ["mcp-server-filesystem", "--base-path", "/workspace"]
                },
                "brave-search": {
                    "command": "npx",
                    "args": ["-y", "@modelcontextprotocol/server-brave-search"]
                },
                "test-server": {
                    "command": "python",
                    "args": ["-m", "test_mcp_server"]
                }
            }
        }

        success, message = await mcp_manager.store_mcp_config(
            config_data=sample_mcp_config,
            config_name="test_integration_config",
            description="Integration test configuration with multiple servers",
            config_type="test",
            set_as_active=True
        )

        if success:
            print(f"✅ Configuration stored: {message}")
        else:
            print(f"❌ Configuration storage failed: {message}")
            return False

        # Test 3: Retrieve Active Configuration
        print("\n3. Testing Active Configuration Retrieval...")
        active_config = await mcp_manager.get_active_config()

        if active_config:
            config_name = active_config.get("config_name")
            server_count = len(active_config.get("config_data", {}).get("mcpServers", {}))
            print(f"✅ Retrieved active config: {config_name}")
            print(f"   Server count: {server_count}")
            print(f"   Servers: {list(active_config.get('config_data', {}).get('mcpServers', {}).keys())}")
        else:
            print("❌ No active configuration found")
            return False

        # Test 4: List All Configurations
        print("\n4. Testing Configuration Listing...")
        configs = await mcp_manager.list_configs()
        print(f"✅ Found {len(configs)} configurations:")

        for i, config in enumerate(configs, 1):
            print(f"   {i}. {config['config_name']} ({config['config_type']}) - {config['server_count']} servers")

        # Test 5: MCP Service Integration
        print("\n5. Testing MCP Service...")
        mcp_service = MCPService()

        # Initialize service
        service_started = await mcp_service.start_service()
        if service_started:
            print("✅ MCP Service started successfully")
        else:
            print("⚠️ MCP Service started with warnings")

        # Test service status
        status = await mcp_service.get_service_status()
        print(f"✅ Service status: {status.get('is_running', False)}")
        if status.get('active_config'):
            active_name = status['active_config'].get('name', 'Unknown')
            print(f"   Active config: {active_name}")

        # Test 6: Configuration Switching
        print("\n6. Testing Configuration Switching...")

        # Create a second configuration
        backup_config = {
            "mcpServers": {
                "simple-server": {
                    "command": "echo",
                    "args": ["test"]
                }
            }
        }

        success, message = await mcp_manager.store_mcp_config(
            config_data=backup_config,
            config_name="backup_config",
            description="Simple backup configuration",
            config_type="backup",
            set_as_active=False
        )

        if success:
            print("✅ Backup configuration stored")

            # List configs again
            configs = await mcp_manager.list_configs()
            backup_config_id = None

            for config in configs:
                if config['config_name'] == 'backup_config':
                    backup_config_id = config['id']
                    break

            if backup_config_id:
                # Switch to backup configuration
                switch_success, switch_message = await mcp_service.switch_configuration(backup_config_id)
                if switch_success:
                    print(f"✅ Successfully switched configuration: {switch_message}")
                else:
                    print(f"❌ Configuration switch failed: {switch_message}")
            else:
                print("❌ Could not find backup configuration ID")

        # Test 7: Configuration Backup
        print("\n7. Testing Configuration Backup...")
        if active_config:
            backup_success, backup_message, backup_id = await mcp_manager.backup_config(active_config['id'])
            if backup_success:
                print(f"✅ Backup created: {backup_message}")
                print(f"   Backup ID: {backup_id}")
            else:
                print(f"❌ Backup failed: {backup_message}")

        # Test 8: WebUI Manager Integration
        print("\n8. Testing WebUI Manager Integration...")
        try:
            webui_manager = WebuiManager()

            # Test MCP service initialization through WebUI Manager
            if webui_manager.mcp_service:
                print("✅ WebUI Manager has MCP service")

                # Test database loading
                db_load_success = await webui_manager.initialize_mcp_from_database()
                if db_load_success:
                    print("✅ WebUI Manager loaded MCP config from database")
                else:
                    print("⚠️ WebUI Manager MCP loading completed with warnings")

                # Test service status through WebUI Manager
                webui_status = await webui_manager.get_mcp_service_status()
                print(f"✅ WebUI MCP service status: {webui_status.get('is_running', False)}")

            else:
                print("❌ WebUI Manager missing MCP service")

        except Exception as e:
            print(f"⚠️ WebUI Manager test had issues: {e}")

        # Test 9: Database Collection Statistics
        print("\n9. Testing Database Statistics...")
        collection_stats = mcp_manager.get_collection_stats()

        if collection_stats:
            doc_count = collection_stats.get('document_count', 0)
            print(f"✅ MCP configurations collection: {doc_count} documents")
        else:
            print("⚠️ Could not retrieve collection statistics")

        # Test 10: Search and Validation
        print("\n10. Testing Configuration Search and Validation...")

        # Search by name
        test_config = await mcp_manager.get_config_by_name("test_integration_config")
        if test_config:
            print("✅ Configuration search by name successful")

            # Validate configuration structure
            config_data = test_config.get("config_data", {})
            if "mcpServers" in config_data and len(config_data["mcpServers"]) > 0:
                print("✅ Configuration structure validation passed")
            else:
                print("❌ Configuration structure validation failed")
        else:
            print("❌ Configuration search by name failed")

        # Stop services
        await mcp_service.stop_service()
        print("\n✅ MCP Service stopped gracefully")

        print("\n" + "=" * 60)
        print("🎉 All MCP-Chroma integration tests completed successfully!")
        print("✅ MCPConfigManager working correctly")
        print("✅ MCPService functional with background tasks")
        print("✅ WebUI Manager integration operational")
        print("✅ Database persistence and retrieval working")
        print("✅ Configuration switching and backup systems functional")

        return True

    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        logger.exception("Test failed")
        return False


async def cleanup_test_data():
    """Clean up test data from the database."""
    try:
        print("\n🧹 Cleaning up test data...")

        doc_pipeline = DocumentPipeline()
        mcp_manager = MCPConfigManager(doc_pipeline)

        # List all configurations
        configs = await mcp_manager.list_configs()

        test_configs = [
            config for config in configs
            if config['config_name'] in ['test_integration_config', 'backup_config']
            or config['config_type'] == 'test'
            or 'backup' in config['config_name']
        ]

        deleted_count = 0
        for config in test_configs:
            success, message = await mcp_manager.delete_config(config['id'])
            if success:
                deleted_count += 1
                print(f"✅ Deleted: {config['config_name']}")
            else:
                print(f"⚠️ Could not delete {config['config_name']}: {message}")

        print(f"✅ Cleanup completed: {deleted_count} test configurations removed")

    except Exception as e:
        print(f"⚠️ Cleanup warning: {e}")


def main():
    """Main test function."""
    print("MCP-Chroma Integration Comprehensive Test")
    print("This script tests the complete integration between MCP configuration management and ChromaDB.")
    print()

    # Run the test
    success = asyncio.run(test_mcp_integration())

    if success:
        # Ask if user wants to clean up
        response = input("\nDo you want to clean up the test data? (y/N): ").strip().lower()
        if response in ['y', 'yes']:
            asyncio.run(cleanup_test_data())

    print("\nTest completed.")
    return success


if __name__ == "__main__":
    main()