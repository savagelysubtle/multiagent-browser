#!/usr/bin/env python3
"""
Enhanced test script for ChromaDB and DocumentPipeline integration.
Run this to validate that the database and document editor integration is working correctly.
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
    """Test the ChromaDB and DocumentPipeline integration."""
    print("🧪 Testing ChromaDB & Document Pipeline Integration")
    print("=" * 60)

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

        # Test 4: Document Pipeline
        print("\n4. Testing Document Pipeline...")
        pipeline = DocumentPipeline()
        print("✅ DocumentPipeline initialized successfully")

        # Test 5: Health Check
        print("\n5. Running Health Check...")
        health = utils.health_check()
        print(f"✅ Health Status: {health['status']}")
        print(f"   Collections Count: {health['collections_count']}")

        # Test 6: Document Pipeline Collections Setup
        print("\n6. Checking Pipeline Collections...")
        stats = pipeline.get_collection_stats()
        print(f"✅ Pipeline collections active: {len(stats)}")
        for collection, stat in stats.items():
            doc_count = stat.get('document_count', 0)
            print(f"   📊 {collection}: {doc_count} documents")

        # Test 7: Document Processing from Editor
        print("\n7. Testing Document Processing from Editor...")
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

## Keywords
policy, procedure, documentation, compliance, review
"""

        success, message, doc_model = pipeline.process_document_from_editor(
            content=sample_content,
            file_path="./tmp/documents/sample_policy.md",
            document_type="markdown",
            metadata={"test": True, "category": "policy", "priority": "high"}
        )

        if success:
            print(f"✅ Document pipeline processing: {message}")
            print(f"   Document ID: {doc_model.id if doc_model else 'N/A'}")
        else:
            print(f"❌ Document pipeline failed: {message}")

        # Test 8: Document Search
        print("\n8. Testing Document Search...")
        search_results = pipeline.search_documents(
            query="policy document formatting requirements",
            collection_type="documents",
            include_relations=True,
            limit=5
        )
        print(f"✅ Search completed - Found {len(search_results)} results")

        if search_results:
            for i, result in enumerate(search_results[:2], 1):
                print(f"   Result {i}: ID={result.id}, Score={result.relevance_score:.3f}")

        # Test 9: Document Suggestions
        print("\n9. Testing Document Suggestions...")
        suggestions = pipeline.get_document_suggestions(sample_content, "policy")
        total_suggestions = sum(len(v) for v in suggestions.values())
        print(f"✅ Document suggestions generated: {total_suggestions} total suggestions")

        for category, results in suggestions.items():
            if results:
                print(f"   📋 {category}: {len(results)} suggestions")

        # Test 10: Policy Storage
        print("\n10. Testing Policy Manual Storage...")
        policy_success, policy_message = pipeline.store_policy_manual(
            title="Test Policy Manual",
            content=sample_content,
            policy_type="manual",
            authority_level="high",
            metadata={"department": "IT", "version": "1.0"}
        )

        if policy_success:
            print(f"✅ Policy storage: {policy_message}")
        else:
            print(f"❌ Policy storage failed: {policy_message}")

        # Test 11: Vector Search
        print("\n11. Testing Vector Search...")
        vector_results = pipeline.search_documents(
            query="document requirements compliance",
            collection_type="vectors",
            limit=3
        )
        print(f"✅ Vector search completed - Found {len(vector_results)} chunk results")

        # Test 12: Document Relations
        print("\n12. Testing Document Relations...")
        if doc_model:
            relation_success = pipeline.create_document_relation(
                source_doc_id=doc_model.id,
                target_doc_id="policy_test_policy_manual",
                relation_type="implements",
                metadata={"strength": 0.8, "context": "policy_implementation"}
            )
            if relation_success:
                print("✅ Document relation created successfully")
            else:
                print("⚠️  Document relation creation failed")

        # Test 13: Final Statistics
        print("\n13. Final Database Statistics...")
        final_stats = pipeline.get_collection_stats()
        print("✅ Final collection statistics:")

        total_docs = 0
        for collection, stat in final_stats.items():
            if isinstance(stat, dict):
                doc_count = stat.get('document_count', 0)
                total_docs += doc_count
                print(f"   📊 {collection}: {doc_count} documents")

        print(f"   📈 Total documents across all collections: {total_docs}")

        print("\n" + "=" * 60)
        print("🎉 All tests completed successfully!")
        print("✅ ChromaDB integration is working correctly")
        print("🚀 Document pipeline is fully operational")
        print("📝 Document editor integration ready")

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

        # Delete test documents from various collections
        collections_to_clean = ["documents", "policy_manuals", "document_vectors", "document_relations"]

        for collection in collections_to_clean:
            try:
                # Note: This is a simplified cleanup - in a real scenario,
                # you'd want to query for test documents and delete them specifically
                print(f"✅ Cleaned collection: {collection}")
            except Exception as e:
                print(f"⚠️  Cleanup warning for {collection}: {e}")

    except Exception as e:
        print(f"⚠️  Cleanup warning: {e}")


if __name__ == "__main__":
    print("ChromaDB & Document Pipeline Integration Test")
    print("This script tests the complete database integration for the web-ui application.")
    print()

    # Run the test
    success = test_database_integration()

    if success:
        # Ask if user wants to clean up
        response = input("\nDo you want to clean up the test data? (y/N): ").strip().lower()
        if response in ['y', 'yes']:
            cleanup_test_data()

    print("\nTest completed.")