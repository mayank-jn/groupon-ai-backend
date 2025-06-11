#!/usr/bin/env python3
"""
Demo script showing enhanced Confluence metadata structure with version tracking.
"""

def show_enhanced_metadata():
    print("🎯 ENHANCED CONFLUENCE METADATA WITH VERSION TRACKING")
    print("=" * 65)
    
    sample_metadata = {
        # Content and identification
        "text": "Sample page content (truncated)...",
        "source": "Engineering Guidelines", 
        "source_type": "confluence",
        "source_id": "confluence_123456789",
        "title": "Engineering Guidelines",
        
        # Confluence-specific metadata
        "page_id": "123456789",
        "space_key": "Engineerin", 
        "space_name": "Engineering",
        
        # ✅ VERSION TRACKING (Critical for detecting stale embeddings)
        "version": 17,
        "version_when": "2024-01-15T10:30:00.000Z",
        "last_modified": "2024-01-15T10:30:00.000Z", 
        "created": "2024-01-01T09:00:00.000Z",
        
        # Author information
        "author": "Mayank Jain",
        "author_id": "6396b964914b350865d19146",
        
        # Content processing metadata
        "chunk_index": 0,
        "total_chunks": 1,
        "was_chunked": False,
        "original_token_count": 500,
        "chunk_token_count": 500,
        
        # Processing info
        "processor": "ConfluenceAdapter",
        "embedding_model": "text-embedding-3-small",
        "ingested_at": "2024-01-15T11:00:00.000Z",
        
        # Access control (prepared for future use)
        "allowed_user_ids": [],
        "visibility": "internal",
        
        # Optional fields
        "tags": ["engineering", "guidelines"],
        "url": "https://mayank66jain.atlassian.net/wiki/pages/viewpage.action?pageId=123456789"
    }
    
    print("📋 METADATA FIELDS:")
    for key, value in sample_metadata.items():
        indicator = "🔑" if key in ["version", "version_when", "last_modified"] else "  "
        print(f"{indicator} {key:20} : {value}")
    
    print("\n🔑 KEY BENEFITS:")
    print("   • VERSION field enables staleness detection")
    print("   • LAST_MODIFIED provides timestamp comparison")
    print("   • AUTHOR_ID supports access control")
    print("   • INGESTED_AT tracks when embedding was created")
    print("   • PAGE_ID enables targeted updates")
    
    print("\n💡 STALENESS DETECTION WORKFLOW:")
    print("   1. Get current page version from Confluence API")
    print("   2. Compare with 'version' field in stored metadata")
    print("   3. If current > stored → re-ingest page")
    print("   4. Update embedding with new version metadata")


if __name__ == "__main__":
    show_enhanced_metadata()
    print("\n✅ Version tracking implemented in your Confluence adapter!") 