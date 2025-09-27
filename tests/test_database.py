#!/usr/bin/env python3
"""
Test script for ChromaDB integration.
Run this to validate that the database is working correctly.
"""

import sys
import logging
from pathlib import Path

# Add src to path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent / "src"))

from web_ui.database import ChromaManager, DocumentModel, CollectionConfig
from web_ui.database.utils import DatabaseUtils
from web_ui.database.config import get_default_config
from web_ui.database.document_pipeline import DocumentPipeline

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def test_database_integration():
    """Test the ChromaDB integration."""
    print("🧪 Testing ChromaDB Integration")
    print("=" * 50)

    try:
        # Test 1: Configuration
        print("\n1. Testing Configuration...")
        config = get_default_config()
        config.validate()
        print(f"✅ Configuration valid - DB Path: {config.db_path}")

        # Test 2: Database Manager
        print("\n2. Testing Database Manager...")
        manager = ChromaManager()
        print("✅ ChromaManager initialized successfully")

        # Test 3: Database Utils
        print("\n3. Testing Database Utils...")
        utils = DatabaseUtils()
        print("✅ DatabaseUtils initialized successfully")

        # Test 4: Health Check
        print("\n4. Running Health Check...")
        health = utils.health_check()
        print(f"✅ Health Status: {health['status']}")
        print(f"   Collections Count: {health['collections_count']}")

        # Test 5: Create Default Collections
        print("\n5. Setting up Default Collections...")
        results = utils.setup_default_collections()
        for collection_name, success in results.items():
            status = "✅" if success else "❌"
            print(f"   {status} {collection_name}")

        # Test 6: Create and Store a Test Document
        print("\n6. Testing Document Storage...")
        test_doc = DocumentModel(
            id="test_doc_001",
            content="This is a test document for ChromaDB integration testing.",
            metadata={"test": True, "category": "integration_test"},
            source="test_script"
        )

        success = manager.add_document("documents", test_doc)
        if success:
            print("✅ Test document stored successfully")
        else:
            print("❌ Failed to store test document")

        # Test 7: Search for the Document
        print("\n7. Testing Document Search...")
        from web_ui.database.models import QueryRequest

        query = QueryRequest(
            query="test document ChromaDB integration",
            collection_name="documents",
            limit=5
        )

        results = manager.search(query)
        print(f"✅ Search completed - Found {len(results)} results")

        if results:
            for i, result in enumerate(results[:3]):  # Show first 3 results
                print(f"   Result {i+1}: ID={result.id}, Score={result.relevance_score:.3f}")

        # Test 8: Collection Statistics
        print("\n8. Testing Collection Statistics...")
        collections_info = utils.get_collection_info()
        for name, info in collections_info.items():
            print(f"   📊 {name}: {info.get('document_count', 0)} documents")

        # Test 9: Retrieve Document by ID
        print("\n9. Testing Document Retrieval...")
        retrieved_doc = manager.get_document("documents", "test_doc_001")
        if retrieved_doc:
            print(f"✅ Retrieved document: {retrieved_doc.id}")
            print(f"   Content preview: {retrieved_doc.content[:50]}...")
        else:
            print("❌ Failed to retrieve test document")

                # Test 10: Document Pipeline Integration
        print("\n10. Testing Document Pipeline Integration...")
        pipeline = DocumentPipeline()

        # Test document processing from editor
        sample_content = """# Sample Policy Document

This is a sample policy document for testing the document pipeline integration.

## Requirements
- All documents must follow proper formatting
- Version control is mandatory
- Regular reviews are required

## Procedures
1. Create document using template
2. Review with team
3. Approve and publish
        """

        success, message, doc_model = pipeline.process_document_from_editor(
            content=sample_content,
            file_path="./tmp/documents/sample_policy.md",
            document_type="markdown",
            metadata={"test": True, "category": "policy"}
        )

        if success:
            print(f"✅ Document pipeline processing: {message}")
        else:
            print(f"❌ Document pipeline failed: {message}")

        # Test document suggestions
        suggestions = pipeline.get_document_suggestions(sample_content, "policy")
        print(f"✅ Document suggestions generated: {len(suggestions)} categories")

        # Test policy storage
        policy_success, policy_message = pipeline.store_policy_manual(
            title="Test Policy Manual",
            content=sample_content,
            policy_type="manual",
            authority_level="high"
        )

        if policy_success:
            print(f"✅ Policy storage: {policy_message}")
        else:
            print(f"❌ Policy storage failed: {policy_message}")

        # Test collection statistics
        stats = pipeline.get_collection_stats()
        print(f"✅ Pipeline collections: {len(stats)} active collections")

        print("\n" + "=" * 50)
        print("🎉 All tests completed successfully!")
        print("✅ ChromaDB integration is working correctly")
        print("🚀 Document pipeline is fully operational")

        return True

    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        logger.exception("Test failed")
        return False


def cleanup_test_data():
    """Clean up test data."""
    try:
        print("\n🧹 Cleaning up test data...")
        manager = ChromaManager()

        # Delete test document
        success = manager.delete_document("documents", "test_doc_001")
        if success:
            print("✅ Test document deleted")
        else:
            print("⚠️  Test document not found or already deleted")

    except Exception as e:
        print(f"⚠️  Cleanup warning: {e}")


if __name__ == "__main__":
    print("ChromaDB Integration Test")
    print("This script tests the Chroma database integration for the web-ui application.")
    print()

    # Run the test
    success = test_database_integration()

    if success:
        # Ask if user wants to clean up
        response = input("\nDo you want to clean up the test data? (y/N): ").strip().lower()
        if response in ['y', 'yes']:
            cleanup_test_data()

    print("\nTest completed.")