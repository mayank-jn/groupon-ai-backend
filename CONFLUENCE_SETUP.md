# Confluence Adapter Setup Guide

## Overview

The Confluence adapter enables the Groupon AI Knowledge Assistant to ingest content from Atlassian Confluence spaces, making your organization's knowledge base searchable through natural language queries with complete metadata preservation and semantic understanding.

**Key Features:**
- ✅ **Production Ready**: Fully implemented and tested Confluence integration
- ✅ **Complete Space Ingestion**: Crawl entire spaces with pagination support
- ✅ **Rich Metadata**: Preserves authors, tags, spaces, URLs, and version history
- ✅ **HTML Processing**: Converts Confluence HTML to clean, searchable text
- ✅ **Multiple Authentication**: Supports both API tokens and bearer tokens
- ✅ **Unified Search**: Integrates seamlessly with GitHub and document search

## Prerequisites

### 1. Install Dependencies
```bash
cd groupon-ai-backend
pip install atlassian-python-api beautifulsoup4 html2text
```

### 2. Confluence Access Setup

#### Option A: API Token (Recommended)
1. Go to [Atlassian Account Settings](https://id.atlassian.com/manage-profile/security/api-tokens)
2. Create a new API token
3. Note your Confluence URL and username

#### Option B: Bearer Token
1. Generate a bearer token through your Confluence admin panel
2. Note your Confluence URL

### 3. Environment Variables

Add to your `.env` file:

```bash
# Confluence Integration (Required)
CONFLUENCE_URL=https://your-company.atlassian.net/wiki
CONFLUENCE_USERNAME=your.email@company.com
CONFLUENCE_API_TOKEN=your_api_token_here

# Option B: Bearer Token (alternative)
# CONFLUENCE_URL=https://your-company.atlassian.net/wiki
# CONFLUENCE_TOKEN=your_bearer_token_here

# Existing OpenAI/Qdrant settings (Required)
OPENAI_API_KEY=your_openai_key
QDRANT_URL=your_qdrant_url
QDRANT_API_KEY=your_qdrant_key
```

## ✅ Verified Working Setup

The Confluence adapter has been successfully tested and deployed with the following configuration:

### Working Environment Variables
```bash
CONFLUENCE_URL=https://mayank66jain.atlassian.net/wiki
CONFLUENCE_USERNAME=mayank66jain@gmail.com
CONFLUENCE_API_TOKEN=ATATT3xFfGF0ZTODn_Uk36w8BVw123yoCI5hKyKh99j5FNLApty1MZaX6zIz6pmMC11hF1tYtnlrMIjHdP-ynon...
```

### Verified Spaces
- **"Engineerin"** (Key: "Engineerin") - Engineering space with 5 pages
- **"SD"** (Key: "SD") - Software development space with 4 pages
- **"MAYANK JAIN"** (Key: "~6396b964914b350865d19146") - Personal space

## Usage

### 1. Via API Endpoint (Production Ready)

#### Ingest Engineering Space
```bash
curl -X POST "http://localhost:8000/confluence/ingest" \
  -H "Content-Type: application/json" \
  -d '{
    "max_pages": 50,
    "source_input": {
      "space_key": "Engineerin"
    }
  }'
```

**Successful Response:**
```json
{
  "status": "success",
  "pages_processed": 5,
  "chunks_uploaded": 5,
  "spaces": ["Engineerin"],
  "source_type": "confluence",
  "embedding_model": "text-embedding-3-small",
  "processing_summary": {
    "total_pages": 5,
    "total_chunks": 5,
    "avg_chunks_per_page": 1.0
  }
}
```

#### Ingest Software Development Space
```bash
curl -X POST "http://localhost:8000/confluence/ingest" \
  -H "Content-Type: application/json" \
  -d '{
    "max_pages": 50,
    "source_input": {
      "space_key": "SD"
    }
  }'
```

#### Ingest Specific Page
```bash
curl -X POST "http://localhost:8000/confluence/ingest" \
  -H "Content-Type: application/json" \
  -d '{
    "source_input": {
      "page_id": "123456789"
    }
  }'
```

#### Search and Ingest
```bash
curl -X POST "http://localhost:8000/confluence/ingest" \
  -H "Content-Type: application/json" \
  -d '{
    "source_input": {
      "search_query": "engineering guidelines",
      "space_key": "Engineerin"
    },
    "max_pages": 10
  }'
```

### 2. Unified Search Integration

Once ingested, Confluence content is automatically available in the unified search:

```bash
curl -X POST "http://localhost:8000/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "engineering processes and guidelines"
  }'
```

### 3. Direct Adapter Usage

#### Python Code Example
```python
from sources.confluence.adapter import ConfluenceAdapter

# Configure adapter
config = {
    'confluence_url': 'https://company.atlassian.net/wiki',
    'username': 'user@company.com',
    'api_token': 'your_api_token',
    'embedding_model': 'text-embedding-3-small',
    'max_pages': 100
}

adapter = ConfluenceAdapter(config)

# Initialize connection
if adapter.initialize():
    # Process a space
    results = adapter.process_source({'space_key': 'Engineerin'})
    
    # Process search results
    results = adapter.process_source({
        'search_query': 'API documentation',
        'space_key': 'Engineerin'
    })
    
    # Process specific page
    results = adapter.process_source({'page_id': '123456789'})
    
    print(f"Processed {len(results)} content chunks")
    
    adapter.cleanup()
```

## Input Types

### Dictionary Input (Recommended)

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `space_key` | string | Confluence space key | `"Engineerin"` |
| `page_id` | string | Specific page ID | `"123456789"` |
| `search_query` | string | Search terms | `"engineering guidelines"` |
| `page_url` | string | Full page URL | `"https://company.atlassian.net/wiki/pages/123"` |
| `title_filter` | string | Filter pages by title (with space_key) | `"API"` |
| `label_filter` | string | Filter pages by label (with space_key) | `"documentation"` |

### String Input (Auto-detected)

The adapter will automatically detect the input type:
- **All digits**: Treated as page ID
- **Single uppercase word**: Treated as space key  
- **Multiple words**: Treated as search query

```python
# These are equivalent
adapter.process_source("Engineerin")
adapter.process_source({"space_key": "Engineerin"})

adapter.process_source("123456789")  
adapter.process_source({"page_id": "123456789"})

adapter.process_source("engineering guidelines")
adapter.process_source({"search_query": "engineering guidelines"})
```

## Configuration Options

| Option | Default | Description |
|--------|---------|-------------|
| `confluence_url` | Required | Your Confluence base URL |
| `username` | Optional | Username for API token auth |
| `api_token` | Optional | API token for authentication |
| `token` | Optional | Bearer token (alternative auth) |
| `embedding_model` | `text-embedding-3-small` | OpenAI embedding model |
| `max_pages` | 100 | Maximum pages to process per request |

## Advanced Features

### Filtered Space Processing
```python
# Only pages with "API" in the title
source_input = {
    "space_key": "Engineerin",
    "title_filter": "API"
}

# Only pages with "documentation" label
source_input = {
    "space_key": "Engineerin", 
    "label_filter": "documentation"
}
```

### Search with Space Restriction
```python
# Search only within specific space
source_input = {
    "search_query": "deployment guide",
    "space_key": "SD"  # Optional: restrict to this space
}
```

## Enhanced Metadata Features

### Rich Metadata Extraction
- **Page Information**: Title, ID, space key, space name
- **Author Details**: Display name, account ID
- **Version Tracking**: Version number, modification timestamps
- **Content Structure**: Chunk index, total chunks, token counts
- **Labels**: Confluence labels as searchable tags
- **URLs**: Direct links to original pages

### Example Metadata Output
```json
{
  "space_key": "Engineerin",
  "space_name": "Engineering",
  "page_id": "123456789",
  "version_number": 5,
  "author": "John Doe",
  "author_id": "user123",
  "creation_date": "2024-01-15T10:30:00Z",
  "last_modified": "2024-06-18T14:22:00Z",
  "chunk_index": 0,
  "total_chunks": 1,
  "was_chunked": false,
  "original_token_count": 450,
  "chunk_token_count": 450,
  "processor": "ConfluenceAdapter"
}
```

## Testing

### 1. Connection Test
```bash
cd groupon-ai-backend
python -c "
from sources.confluence.adapter import ConfluenceAdapter
import os
from dotenv import load_dotenv
load_dotenv()

config = {
    'confluence_url': os.getenv('CONFLUENCE_URL'),
    'username': os.getenv('CONFLUENCE_USERNAME'),
    'api_token': os.getenv('CONFLUENCE_API_TOKEN')
}

adapter = ConfluenceAdapter(config)
if adapter.initialize():
    print('✅ Connection successful!')
else:
    print('❌ Connection failed!')
"
```

### 2. List Available Spaces
```bash
curl -X POST "http://localhost:8000/confluence/ingest" \
  -H "Content-Type: application/json" \
  -d '{
    "source_input": {
      "space_key": "TEST"
    },
    "max_pages": 1
  }'
```

### 3. Test Specific Space Access
```bash
# Test with known working space
curl -X POST "http://localhost:8000/confluence/ingest" \
  -H "Content-Type: application/json" \
  -d '{
    "source_input": {
      "space_key": "Engineerin"
    },
    "max_pages": 3
  }'
```

## Integration with Existing System

The Confluence adapter seamlessly integrates with your existing infrastructure:

### ✅ **Unified Vector Database**
- Same Qdrant collection as GitHub and document uploads
- Consistent metadata structure across all sources
- Unified search experience with source attribution

### ✅ **Enhanced Search Results** 
- Confluence pages appear in unified search results
- Rich metadata includes space, author, and version information
- Direct links back to original Confluence pages

### ✅ **Source Adapter Pattern**
- Registered with `SourceFactory` for automatic discovery
- Available via `/sources` endpoint
- Consistent interface with other adapters

## Troubleshooting

### Common Issues

#### 1. Authentication Errors
```
Error: The calling user does not have permission to view the content
```
**Solution**: 
- Verify your API token has access to the specific space
- Check space permissions in Confluence admin
- Ensure the space key is correct (case-sensitive)

#### 2. Space Not Found
```
Error: No content found or processed
```
**Solution**:
- Use correct space key (check available spaces)
- Verify space exists and is accessible
- Try with a different space or page ID

#### 3. Connection Issues
```
Error: Failed to connect to Confluence
```
**Solution**:
- Verify `CONFLUENCE_URL` is correct
- Check network connectivity
- Validate API token is not expired

### Debug Commands

```bash
# Check environment variables
env | grep CONFLUENCE

# Test API endpoint directly
curl -X GET "https://your-company.atlassian.net/wiki/rest/api/space" \
  -H "Authorization: Basic $(echo -n 'username:api_token' | base64)"

# Check available source adapters
curl http://localhost:8000/sources
```

### Space Key Reference

When setting up Confluence ingestion, use these verified space keys:

| Space Name | Space Key | Status |
|------------|-----------|--------|
| Engineering | `"Engineerin"` | ✅ Working |
| Software Development | `"SD"` | ✅ Working |
| Personal Spaces | `"~user_id"` | ✅ Working |

## Production Deployment

### Environment Variables for Production
```bash
# Production Confluence Setup
CONFLUENCE_URL=https://company.atlassian.net/wiki
CONFLUENCE_USERNAME=service-account@company.com
CONFLUENCE_API_TOKEN=production_token_here

# Recommended settings
MAX_PAGES_DEFAULT=50
EMBEDDING_MODEL=text-embedding-3-small
```

### Performance Considerations
- **Rate Limiting**: Confluence API has rate limits, adapter handles this automatically
- **Large Spaces**: Use `max_pages` parameter to control ingestion size
- **Memory Usage**: Large pages are automatically chunked for optimal processing
- **Incremental Updates**: Re-run ingestion to update with latest content

This Confluence adapter provides a production-ready solution for integrating Confluence knowledge bases into your AI-powered search system, with comprehensive metadata preservation and seamless integration with existing document and code search capabilities. 