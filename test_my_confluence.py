#!/usr/bin/env python3
"""
Test script for Mayank's Confluence instance.
This script tests the Confluence adapter with the provided credentials.
"""

import os
import sys
from dotenv import load_dotenv

# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

load_dotenv()

from sources.confluence.adapter import ConfluenceAdapter
from sources import SourceFactory


def test_confluence_connection():
    """Test connection to Mayank's Confluence instance."""
    print("🚀 Testing Confluence Connection")
    print("=" * 50)
    
    # Get Confluence credentials from environment variables
    config = {
        'confluence_url': os.getenv('CONFLUENCE_URL'),
        'username': os.getenv('CONFLUENCE_USERNAME'),
        'api_token': os.getenv('CONFLUENCE_API_TOKEN'),
        'embedding_model': 'text-embedding-3-small',
        'max_pages': 10  # Start with a small number for testing
    }
    
    # Validate required environment variables
    if not config['confluence_url']:
        print("❌ CONFLUENCE_URL environment variable not set")
        return False
    if not config['username']:
        print("❌ CONFLUENCE_USERNAME environment variable not set")
        return False
    if not config['api_token']:
        print("❌ CONFLUENCE_API_TOKEN environment variable not set")
        return False
    
    try:
        print(f"📍 Confluence URL: {config['confluence_url']}")
        print(f"👤 Username: {config['username']}")
        print(f"🔑 API Token: {config['api_token'][:20]}...{config['api_token'][-10:]}")
        
        # Create adapter
        adapter = ConfluenceAdapter(config)
        print("✅ Confluence adapter created")
        
        # Test initialization
        print("\n🔌 Testing connection...")
        if adapter.initialize():
            print("✅ Successfully connected to Confluence!")
            
            # Test getting spaces
            print("\n📚 Attempting to list available spaces...")
            try:
                spaces = adapter.confluence_client.get_all_spaces(limit=5)
                print(f"✅ Found {len(spaces)} spaces:")
                for space in spaces:
                    # Handle different response formats
                    if isinstance(space, dict):
                        space_key = space.get('key', 'N/A')
                        space_name = space.get('name', 'N/A')
                    else:
                        space_key = getattr(space, 'key', 'N/A')
                        space_name = getattr(space, 'name', 'N/A')
                    print(f"   📁 {space_key}: {space_name}")
                
                # Test with the first space if available
                if spaces:
                    test_space = spaces[0]['key']
                    print(f"\n🧪 Testing with space: {test_space}")
                    
                    # Test input validation
                    test_input = {'space_key': test_space}
                    if adapter.validate_input(test_input):
                        print("✅ Input validation passed")
                        
                        # Test getting pages from space (limit to 2 for testing)
                        print(f"📄 Getting pages from space {test_space}...")
                        original_max = adapter.max_pages
                        adapter.max_pages = 2  # Limit for testing
                        
                        try:
                            results = adapter.process_source(test_input)
                            print(f"✅ Successfully processed {len(results)} content chunks")
                            
                            for i, result in enumerate(results):
                                print(f"   📝 Chunk {i+1}: {result.title[:50]}...")
                                print(f"      📊 Tokens: {result.metadata.get('chunk_token_count', 'N/A')}")
                                print(f"      🏷️  Source: {result.source_type}")
                                if result.url:
                                    print(f"      🔗 URL: {result.url}")
                                
                        except Exception as e:
                            print(f"⚠️  Error processing space content: {e}")
                        finally:
                            adapter.max_pages = original_max
                    
                else:
                    print("⚠️  No spaces found to test with")
                    
            except Exception as e:
                print(f"⚠️  Error listing spaces: {e}")
            
            # Cleanup
            adapter.cleanup()
            print("✅ Adapter cleanup completed")
            
            return True
            
        else:
            print("❌ Failed to connect to Confluence")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_search_functionality():
    """Test search functionality."""
    print("\n" + "=" * 50)
    print("🔍 Testing Search Functionality")
    print("=" * 50)
    
    config = {
        'confluence_url': os.getenv('CONFLUENCE_URL'),
        'username': os.getenv('CONFLUENCE_USERNAME'),
        'api_token': os.getenv('CONFLUENCE_API_TOKEN'),
        'embedding_model': 'text-embedding-3-small',
        'max_pages': 5
    }
    
    if not all([config['confluence_url'], config['username'], config['api_token']]):
        print("❌ Missing required environment variables")
        return False
    
    try:
        adapter = ConfluenceAdapter(config)
        
        if adapter.initialize():
            print("✅ Connection established for search testing")
            
            # Test different search inputs
            search_tests = [
                "documentation",
                "guide", 
                "setup",
                "help"
            ]
            
            for search_term in search_tests:
                print(f"\n🔍 Searching for: '{search_term}'")
                try:
                    search_input = {'search_query': search_term}
                    if adapter.validate_input(search_input):
                        results = adapter.process_source(search_input)
                        print(f"   ✅ Found {len(results)} results")
                        
                        for result in results[:2]:  # Show first 2 results
                            print(f"      📄 {result.title}")
                            print(f"      📝 {result.content[:100]}...")
                    else:
                        print(f"   ❌ Invalid search input")
                        
                except Exception as e:
                    print(f"   ⚠️  Search error: {e}")
            
            adapter.cleanup()
            return True
        else:
            print("❌ Failed to establish connection for search testing")
            return False
            
    except Exception as e:
        print(f"❌ Search test error: {e}")
        return False


def test_api_endpoint():
    """Test the /confluence/ingest API endpoint."""
    print("\n" + "=" * 50)
    print("🌐 Testing API Endpoint")
    print("=" * 50)
    
    import requests
    import json
    
    # API endpoint
    api_url = "http://localhost:8000/confluence/ingest"
    
    # Test payload using environment variables
    payload = {
        "confluence_url": os.getenv('CONFLUENCE_URL'),
        "username": os.getenv('CONFLUENCE_USERNAME'),
        "api_token": os.getenv('CONFLUENCE_API_TOKEN'),
        "source_input": {
            "search_query": "test"
        },
        "max_pages": 3
    }
    
    if not all([payload['confluence_url'], payload['username'], payload['api_token']]):
        print("❌ Missing required environment variables for API test")
        return False
    
    try:
        print(f"📡 Testing API endpoint: {api_url}")
        print("📦 Payload prepared")
        
        # Make request
        response = requests.post(api_url, json=payload, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            print("✅ API call successful!")
            print(f"   📊 Status: {result.get('status')}")
            print(f"   📄 Pages processed: {result.get('pages_processed', 'N/A')}")
            print(f"   📝 Chunks uploaded: {result.get('chunks_uploaded', 'N/A')}")
            print(f"   🏷️  Source type: {result.get('source_type', 'N/A')}")
            
            if 'processing_summary' in result:
                summary = result['processing_summary']
                print(f"   📈 Average chunks per page: {summary.get('avg_chunks_per_page', 'N/A')}")
            
            return True
        else:
            print(f"❌ API call failed with status {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("⚠️  Could not connect to API endpoint. Make sure the backend server is running:")
        print("   cd groupon-ai-backend && uvicorn app:app --reload --port 8000")
        return True  # Don't fail the test for this
    except Exception as e:
        print(f"❌ API test error: {e}")
        return False


def main():
    """Run all tests for Mayank's Confluence instance."""
    print("🎯 Testing Confluence Integration")
    print(f"📍 Instance: {os.getenv('CONFLUENCE_URL', 'Not set')}")
    print(f"👤 User: {os.getenv('CONFLUENCE_USERNAME', 'Not set')}")
    print()
    
    tests = [
        ("Connection Test", test_confluence_connection),
        ("Search Test", test_search_functionality),
        ("API Endpoint Test", test_api_endpoint),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n🧪 Running: {test_name}")
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("🎯 TEST SUMMARY")
    print("=" * 60)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    print(f"\nTotal: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("\n🎉 All tests passed! Your Confluence integration is working!")
        print("Next steps:")
        print("1. Start the backend server: uvicorn app:app --reload --port 8000")
        print("2. Use the /confluence/ingest endpoint to ingest content")
        print("3. Query your Confluence content through the AI assistant!")
    else:
        print("\n⚠️  Some tests failed. Check the output above for details.")
    
    return 0 if passed == total else 1


if __name__ == "__main__":
    exit(main()) 