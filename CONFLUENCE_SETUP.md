# Confluence Adapter Setup Guide

## Overview

The Confluence adapter enables the Groupon AI Knowledge Assistant to ingest content from Atlassian Confluence spaces, making your organization's knowledge base searchable through natural language queries. 

**Key Features:**
- ✅ **Reuses Existing Infrastructure**: Leverages the same Qdrant vector database and OpenAI embeddings
- ✅ **Multiple Input Types**: Supports space keys, page IDs, search queries, and URLs
- ✅ **Conditional Chunking**: Automatically chunks large pages using the existing token-based logic
- ✅ **Rich Metadata**: Preserves authors, tags, spaces, and URLs for context
- ✅ **HTML Processing**: Converts Confluence HTML to clean, searchable text
- ✅ **Flexible Authentication**: Supports both API tokens and bearer tokens

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
# Option A: Username + API Token
CONFLUENCE_URL=https://your-company.atlassian.net/wiki
CONFLUENCE_USERNAME=your.email@company.com
CONFLUENCE_API_TOKEN=your_api_token_here

# Option B: Bearer Token (alternative)
CONFLUENCE_URL=https://your-company.atlassian.net/wiki
CONFLUENCE_TOKEN=your_bearer_token_here

# Existing OpenAI/Qdrant settings
OPENAI_API_KEY=your_openai_key
QDRANT_URL=your_qdrant_url
QDRANT_API_KEY=your_qdrant_key
```

## Usage

### 1. Via API Endpoint

#### Ingest Entire Space
```bash
curl -X POST "http://localhost:8000/confluence/ingest" \
  -H "Content-Type: application/json" \
  -d '{
    "confluence_url": "https://company.atlassian.net/wiki",
    "username": "user@company.com",
    "api_token": "your_token",
    "source_input": {
      "space_key": "ENGINEERING"
    },
    "max_pages": 50
  }'
```

#### Ingest Specific Page
```bash
curl -X POST "http://localhost:8000/confluence/ingest" \
  -H "Content-Type: application/json" \
  -d '{
    "confluence_url": "https://company.atlassian.net/wiki",
    "username": "user@company.com", 
    "api_token": "your_token",
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
    "confluence_url": "https://company.atlassian.net/wiki",
    "token": "your_bearer_token",
    "source_input": {
      "search_query": "kubernetes deployment",
      "space_key": "DEVOPS"
    }
  }'
```

### 2. Direct Adapter Usage

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
    results = adapter.process_source({'space_key': 'ENGINEERING'})
    
    # Process search results
    results = adapter.process_source({
        'search_query': 'API documentation',
        'space_key': 'ENGINEERING'
    })
    
    # Process specific page
    results = adapter.process_source({'page_id': '123456789'})
    
    # Process from URL
    results = adapter.process_source({
        'page_url': 'https://company.atlassian.net/wiki/pages/123456789'
    })
    
    print(f"Processed {len(results)} content chunks")
    
    adapter.cleanup()
```

## Input Types

### Dictionary Input (Recommended)

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `space_key` | string | Confluence space key | `"ENGINEERING"` |
| `page_id` | string | Specific page ID | `"123456789"` |
| `search_query` | string | Search terms | `"kubernetes deployment"` |
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
adapter.process_source("ENGINEERING")
adapter.process_source({"space_key": "ENGINEERING"})

adapter.process_source("123456789")  
adapter.process_source({"page_id": "123456789"})

adapter.process_source("kubernetes deployment")
adapter.process_source({"search_query": "kubernetes deployment"})
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
| `include_attachments` | False | Whether to process attachments (future) |

## Advanced Features

### Filtered Space Processing
```python
# Only pages with "API" in the title
source_input = {
    "space_key": "ENGINEERING",
    "title_filter": "API"
}

# Only pages with "documentation" label
source_input = {
    "space_key": "ENGINEERING", 
    "label_filter": "documentation"
}
```

### Search with Space Restriction
```python
# Search only within specific space
source_input = {
    "search_query": "deployment guide",
    "space_key": "DEVOPS"  # Optional: restrict to this space
}
```

## Testing

### 1. Run Test Suite
```bash
cd groupon-ai-backend
python test_confluence_adapter.py
```

### 2. Test Specific Functionality
```python
# Test without real Confluence connection
python -c "
from sources.confluence.adapter import ConfluenceAdapter
adapter = ConfluenceAdapter()
print('Capabilities:', adapter.get_capabilities())
print('Validates space key:', adapter.validate_input({'space_key': 'TEST'}))
"
```

### 3. Test with Real Connection
Set environment variables and run:
```bash
python test_confluence_adapter.py
```

## Integration with Existing System

The Confluence adapter seamlessly integrates with your existing infrastructure:

### ✅ **Reuses Qdrant Database**
- Same vector collection as document uploads
- Consistent metadata structure
- Unified search experience

### ✅ **Reuses OpenAI Logic** 
- Same embedding model (`text-embedding-3-small`)
- Conditional chunking based on token limits
- Integrated with Assistant API responses

### ✅ **Factory Pattern**
- Registered with `SourceFactory`
- Available via `/sources` and `/document-info` endpoints
- Consistent adapter interface

## Troubleshooting

### Connection Issues

**Problem**: "Failed to connect to Confluence"
```bash
# Check URL format
✅ https://company.atlassian.net/wiki
❌ https://company.atlassian.net
❌ https://company.atlassian.net/wiki/

# Test connection manually
curl -u "user@company.com:api_token" \
  "https://company.atlassian.net/wiki/rest/api/space"
```

**Problem**: "Authentication failed"
```bash
# Verify API token
curl -u "user@company.com:your_token" \
  "https://company.atlassian.net/wiki/rest/api/user/current"

# Check token permissions
# - Must have space read access
# - Must have page read access
```

### Processing Issues

**Problem**: "No content found"
- Verify space key exists and is accessible
- Check if pages have content (not just attachments)
- Verify search query returns results in Confluence UI

**Problem**: "Token limit exceeded"
- Confluence pages can be very large
- The adapter automatically chunks content
- Consider reducing `max_pages` for initial testing

### API Issues

**Problem**: Rate limiting
- Confluence has API rate limits
- Consider adding delays for large batch processing
- Monitor Confluence admin logs

## Best Practices

### 1. **Start Small**
```python
# Test with limited pages first
config = {'max_pages': 5}
```

### 2. **Use Specific Inputs**
```python
# More efficient than space crawling
{'page_id': '123456'}        # Best
{'search_query': 'specific'} # Good  
{'space_key': 'HUGE_SPACE'}  # Potentially slow
```

### 3. **Monitor Token Usage**
- Large Confluence spaces can generate many API calls
- Each page processed uses OpenAI embedding tokens
- Consider batch processing for cost efficiency

### 4. **Regular Updates**
```python
# For keeping content fresh, consider periodic re-ingestion
# The adapter handles duplicate content by source_id
```

## Next Steps

1. **Test the connection** with your Confluence instance
2. **Start with a small space** to verify functionality  
3. **Scale up gradually** based on your needs
4. **Monitor performance** and adjust `max_pages` as needed
5. **Consider automation** for regular content updates

The Confluence adapter is now ready to make your organization's knowledge searchable through the AI assistant! 🚀 