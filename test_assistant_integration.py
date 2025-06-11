#!/usr/bin/env python3
"""
Test script to verify Assistant API integration and fallback behavior.
"""

import requests
import json
import time

BASE_URL = "http://localhost:8000"  # Change to your backend URL

def test_api_status():
    """Test the API status endpoint."""
    print("=== Testing API Status ===")
    try:
        response = requests.get(f"{BASE_URL}/api-status")
        if response.status_code == 200:
            data = response.json()
            print(f"✓ API Version: {data['version']}")
            print(f"✓ Primary Method: {data['primary_method']}")
            print(f"✓ Fallback Method: {data['fallback_method']}")
            print(f"✓ Features: {', '.join(data['features'])}")
        else:
            print(f"✗ Failed to get API status: {response.status_code}")
    except Exception as e:
        print(f"✗ Error testing API status: {e}")
    print()

def test_search_endpoint():
    """Test the primary search endpoint (Assistant API with fallback)."""
    print("=== Testing Search Endpoint ===")
    
    test_queries = [
        "What is the purpose of the Multi-PDS Integration?",
        "How does the deal restructure process work?",
        "What are the main components of the customer issue tracker?"
    ]
    
    for i, query in enumerate(test_queries, 1):
        print(f"Test {i}: {query}")
        try:
            response = requests.post(
                f"{BASE_URL}/search",
                params={"query": query},
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"✓ Response received")
                print(f"  Answer length: {len(data.get('answer', ''))}")
                
                if data.get('fallback_used'):
                    print(f"  ⚠️ Fallback used: {data.get('fallback_reason', 'Unknown')}")
                    print(f"  ⚠️ Method: {data.get('fallback_used')}")
                else:
                    print(f"  ✓ Primary Assistant API used")
                
                if data.get('error'):
                    print(f"  ⚠️ Error reported: {data['error']}")
                    
            else:
                print(f"✗ Failed with status: {response.status_code}")
                print(f"  Response: {response.text}")
                
        except Exception as e:
            print(f"✗ Error: {e}")
        
        print()
        time.sleep(1)  # Rate limiting

def test_legacy_endpoints():
    """Test the legacy/explicit endpoints."""
    print("=== Testing Legacy Endpoints ===")
    
    test_query = "What is Multi-PDS Integration?"
    
    # Test traditional RAG endpoint
    print("Testing Traditional RAG endpoint:")
    try:
        response = requests.post(
            f"{BASE_URL}/search/traditional",
            params={"query": test_query},
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Traditional RAG response received")
            print(f"  Method: {data.get('method', 'unknown')}")
            print(f"  Answer length: {len(data.get('answer', ''))}")
        else:
            print(f"✗ Traditional RAG failed: {response.status_code}")
    except Exception as e:
        print(f"✗ Traditional RAG error: {e}")
    
    print()
    
    # Test assistant endpoint
    print("Testing Assistant API endpoint:")
    try:
        response = requests.post(
            f"{BASE_URL}/search/assistant",
            params={"query": test_query},
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Assistant API response received")
            print(f"  Method: {data.get('method', 'unknown')}")
            print(f"  Answer length: {len(data.get('answer', ''))}")
        else:
            print(f"✗ Assistant API failed: {response.status_code}")
    except Exception as e:
        print(f"✗ Assistant API error: {e}")
    
    print()

def test_reset_endpoints():
    """Test the reset endpoints."""
    print("=== Testing Reset Endpoints ===")
    
    # Test primary reset endpoint
    print("Testing Primary Reset endpoint:")
    try:
        response = requests.post(f"{BASE_URL}/reset-chat")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Reset successful")
            print(f"  Status: {data.get('status')}")
            print(f"  Message: {data.get('message')}")
            
            if data.get('fallback_used'):
                print(f"  ⚠️ Fallback used: {data.get('fallback_reason')}")
            else:
                print(f"  ✓ Primary Assistant reset used")
                
        else:
            print(f"✗ Reset failed: {response.status_code}")
    except Exception as e:
        print(f"✗ Reset error: {e}")
    
    print()

def test_document_info():
    """Test the enhanced document info endpoint."""
    print("=== Testing Document Info ===")
    try:
        response = requests.get(f"{BASE_URL}/document-info")
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Document info retrieved")
            print(f"  Available adapters: {data.get('available_adapters', [])}")
            print(f"  Architecture: {data.get('architecture')}")
            print(f"  Embedding model: {data.get('embedding_model')}")
        else:
            print(f"✗ Failed to get document info: {response.status_code}")
    except Exception as e:
        print(f"✗ Error: {e}")
    print()

def main():
    """Run all tests."""
    print("🤖 Assistant API Integration Test Suite")
    print("=" * 50)
    
    test_api_status()
    test_search_endpoint()
    test_legacy_endpoints()
    test_reset_endpoints()
    test_document_info()
    
    print("=" * 50)
    print("✅ Test suite completed!")
    print("\nNote: If you see fallback warnings, it means the Assistant API")
    print("is not available but the traditional RAG is working as backup.")

if __name__ == "__main__":
    main() 