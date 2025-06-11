"""
Confluence source adapter.

This adapter handles Confluence page retrieval and processing while reusing
the existing Qdrant database and OpenAI embedding logic.
"""

import os
import re
from typing import List, Dict, Any, Optional, Union
from datetime import datetime
from atlassian import Confluence
import html2text
from bs4 import BeautifulSoup

from sources.base.interfaces import SourceAdapter, SourceResult
from ingest.pdf_ingest import chunk_text_conditionally, count_tokens


class ConfluenceAdapter(SourceAdapter):
    """Source adapter for Confluence integration."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.config = config or {}
        
        # Confluence connection settings
        self.confluence_url = self.config.get('confluence_url')
        self.username = self.config.get('username')
        self.api_token = self.config.get('api_token')
        self.token = self.config.get('token')  # Alternative token method
        
        # Processing settings
        self.embedding_model = self.config.get('embedding_model', 'text-embedding-3-small')
        self.include_attachments = self.config.get('include_attachments', False)
        self.max_pages = self.config.get('max_pages', 100)
        
        # Internal
        self.confluence_client = None
        self.html_converter = html2text.HTML2Text()
        self.html_converter.ignore_links = False
        self.html_converter.body_width = 0  # Don't wrap lines
    
    def get_source_type(self) -> str:
        """Return the type of this source adapter."""
        return 'confluence'
    
    def initialize(self) -> bool:
        """Initialize the Confluence connection."""
        try:
            print(f"DEBUG: Initializing Confluence adapter with URL: {self.confluence_url}")
            print(f"DEBUG: Username: {self.username}")
            print(f"DEBUG: Has API token: {bool(self.api_token)}")
            print(f"DEBUG: Has bearer token: {bool(self.token)}")
            
            if not self.confluence_url:
                raise ValueError("confluence_url is required")
            
            # Initialize Confluence client with different auth methods
            if self.username and self.api_token:
                print("DEBUG: Using username + API token authentication")
                # Username + API token authentication
                self.confluence_client = Confluence(
                    url=self.confluence_url,
                    username=self.username,
                    password=self.api_token,
                    api_version='cloud'
                )
            elif self.token:
                print("DEBUG: Using bearer token authentication")
                # Bearer token authentication
                self.confluence_client = Confluence(
                    url=self.confluence_url,
                    token=self.token
                )
            else:
                raise ValueError("Either (username + api_token) or token is required for authentication")
            
            # Test connection
            try:
                print("DEBUG: Testing Confluence connection...")
                spaces = self.confluence_client.get_all_spaces(limit=1)
                print(f"DEBUG: Connection successful, found {len(spaces)} spaces")
                return True
            except Exception as e:
                print(f"DEBUG: Failed to connect to Confluence: {e}")
                return False
                
        except Exception as e:
            print(f"DEBUG: Failed to initialize Confluence adapter: {e}")
            return False
    
    def validate_input(self, source_input: Any) -> bool:
        """Validate that the input is appropriate for this source adapter."""
        if isinstance(source_input, dict):
            # Dict input with configuration
            return any(key in source_input for key in ['space_key', 'page_id', 'search_query', 'page_url'])
        elif isinstance(source_input, str):
            # String input (space key, page ID, or search query)
            return len(source_input.strip()) > 0
        return False
    
    def process_source(self, source_input: Any, **kwargs) -> List[SourceResult]:
        """Process input from this source and return list of SourceResult objects."""
        if not self.confluence_client:
            raise RuntimeError("Confluence client not initialized. Call initialize() first.")
        
        if isinstance(source_input, dict):
            return self._process_dict_input(source_input, **kwargs)
        elif isinstance(source_input, str):
            return self._process_string_input(source_input, **kwargs)
        else:
            raise ValueError(f"Unsupported input type: {type(source_input)}")
    
    def _process_dict_input(self, input_dict: Dict[str, Any], **kwargs) -> List[SourceResult]:
        """Process dictionary input with specific parameters."""
        results = []
        
        if 'space_key' in input_dict:
            # Process entire space or filtered pages
            space_key = input_dict['space_key']
            title_filter = input_dict.get('title_filter')
            label_filter = input_dict.get('label_filter')
            
            pages = self._get_space_pages(space_key, title_filter, label_filter)
            for page in pages:
                page_results = self._process_page(page)
                results.extend(page_results)
        
        elif 'page_id' in input_dict:
            # Process specific page by ID
            page_id = input_dict['page_id']
            page = self.confluence_client.get_page_by_id(page_id, expand='body.storage,version,space')
            page_results = self._process_page(page)
            results.extend(page_results)
        
        elif 'search_query' in input_dict:
            # Search for pages
            query = input_dict['search_query']
            space_key = input_dict.get('space_key')  # Optional space restriction
            
            pages = self._search_pages(query, space_key)
            for page in pages:
                page_results = self._process_page(page)
                results.extend(page_results)
        
        elif 'page_url' in input_dict:
            # Extract page from URL
            page_url = input_dict['page_url']
            page_id = self._extract_page_id_from_url(page_url)
            if page_id:
                page = self.confluence_client.get_page_by_id(page_id, expand='body.storage,version,space')
                page_results = self._process_page(page)
                results.extend(page_results)
        
        return results
    
    def _process_string_input(self, input_str: str, **kwargs) -> List[SourceResult]:
        """Process string input (space key, page ID, or search query)."""
        input_str = input_str.strip()
        
        # Try to determine input type
        if input_str.isdigit():
            # Looks like a page ID
            return self._process_dict_input({'page_id': input_str}, **kwargs)
        elif len(input_str.split()) == 1 and input_str.isupper():
            # Looks like a space key (typically uppercase)
            return self._process_dict_input({'space_key': input_str}, **kwargs)
        else:
            # Treat as search query
            return self._process_dict_input({'search_query': input_str}, **kwargs)
    
    def _get_space_pages(self, space_key: str, title_filter: Optional[str] = None, 
                        label_filter: Optional[str] = None) -> List[Dict]:
        """Get pages from a Confluence space."""
        try:
            pages = []
            start = 0
            limit = 50
            
            while len(pages) < self.max_pages:
                batch = self.confluence_client.get_all_pages_from_space(
                    space=space_key,
                    start=start,
                    limit=limit,
                    expand='body.storage,version,space'
                )
                
                if not batch:
                    break
                
                # Apply filters
                for page in batch:
                    if title_filter and title_filter.lower() not in page['title'].lower():
                        continue
                    
                    if label_filter:
                        labels = self.confluence_client.get_page_labels(page['id'])
                        label_names = [label['name'] for label in labels.get('results', [])]
                        if label_filter not in label_names:
                            continue
                    
                    pages.append(page)
                    
                    if len(pages) >= self.max_pages:
                        break
                
                start += limit
                
                if len(batch) < limit:
                    break
            
            return pages[:self.max_pages]
            
        except Exception as e:
            print(f"Error getting pages from space {space_key}: {e}")
            return []
    
    def _search_pages(self, query: str, space_key: Optional[str] = None) -> List[Dict]:
        """Search for pages in Confluence."""
        try:
            search_query = f'text ~ "{query}"'
            if space_key:
                search_query += f' and space.key = {space_key}'
            
            results = self.confluence_client.cql(
                cql=search_query,
                limit=self.max_pages,
                expand='body.storage,version,space'
            )
            
            return results.get('results', [])
            
        except Exception as e:
            print(f"Error searching pages with query '{query}': {e}")
            return []
    
    def _extract_page_id_from_url(self, url: str) -> Optional[str]:
        """Extract page ID from Confluence URL."""
        # Match patterns like /pages/123456789 or pageId=123456789
        patterns = [
            r'/pages/(\d+)',
            r'pageId=(\d+)',
            r'/display/.+/([^/]+)$'  # For display URLs, less reliable
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        return None
    
    def _process_page(self, page: Dict) -> List[SourceResult]:
        """Process a single Confluence page into SourceResult objects."""
        try:
            # Extract basic information
            page_id = page['id']
            title = page['title']
            space_key = page['space']['key']
            space_name = page['space']['name']
            
            # Get content
            content_html = page.get('body', {}).get('storage', {}).get('value', '')
            content_text = self._html_to_text(content_html)
            
            # Clean up the content
            content_text = self._clean_content(content_text)
            
            if not content_text.strip():
                return []  # Skip empty pages
            
            # Extract metadata
            version_info = page.get('version', {})
            author = version_info.get('by', {}).get('displayName', 'Unknown')
            author_id = version_info.get('by', {}).get('accountId')
            version_number = version_info.get('number', 1)
            created_date = self._parse_date(version_info.get('when'))
            updated_date = created_date  # Last modified date (version when field)
            
            # Try to get creation date separately (requires additional API call)
            creation_date = None
            try:
                # Get first version to find creation date
                history = self.confluence_client.get_page_history(page_id, limit=1)
                if history and 'results' in history and history['results']:
                    first_version = history['results'][-1]  # Oldest version
                    creation_date = self._parse_date(first_version.get('when'))
            except:
                creation_date = created_date  # Fallback to last modified
            
            # Build URL
            page_url = f"{self.confluence_url.rstrip('/')}/pages/viewpage.action?pageId={page_id}"
            
            # Get labels as tags
            try:
                labels_response = self.confluence_client.get_page_labels(page_id)
                tags = [label['name'] for label in labels_response.get('results', [])]
            except:
                tags = []
            
            # Apply conditional chunking
            original_token_count = count_tokens(content_text, model=self.embedding_model)
            chunks = chunk_text_conditionally(content_text, model=self.embedding_model)
            
            # Create SourceResult objects for each chunk
            results = []
            for i, chunk in enumerate(chunks):
                source_result = SourceResult(
                    content=chunk,
                    metadata={
                        'space_key': space_key,
                        'space_name': space_name,
                        'page_id': page_id,
                        'version_number': version_number,
                        'version_when': version_info.get('when'),
                        'author_id': author_id,
                        'creation_date': creation_date.isoformat() if creation_date else None,
                        'last_modified': updated_date.isoformat() if updated_date else None,
                        'chunk_index': i,
                        'total_chunks': len(chunks),
                        'original_token_count': original_token_count,
                        'chunk_token_count': count_tokens(chunk, model=self.embedding_model),
                        'was_chunked': len(chunks) > 1,
                        'processor': 'ConfluenceAdapter'
                    },
                    source_type=self.get_source_type(),
                    source_id=f"confluence_{page_id}_chunk_{i}" if len(chunks) > 1 else f"confluence_{page_id}",
                    title=f"{title} (Part {i+1})" if len(chunks) > 1 else title,
                    author=author,
                    created_date=created_date,
                    updated_date=updated_date,
                    url=page_url,
                    tags=tags
                )
                results.append(source_result)
            
            return results
            
        except Exception as e:
            print(f"Error processing page {page.get('id', 'unknown')}: {e}")
            return []
    
    def _html_to_text(self, html_content: str) -> str:
        """Convert HTML content to clean text."""
        if not html_content:
            return ""
        
        # Use BeautifulSoup to clean up malformed HTML first
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()
        
        # Convert to text using html2text
        text = self.html_converter.handle(str(soup))
        
        return text
    
    def _clean_content(self, content: str) -> str:
        """Clean and normalize the extracted content."""
        if not content:
            return ""
        
        # Remove excessive whitespace
        content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)  # Multiple blank lines -> double
        content = re.sub(r'[ \t]+', ' ', content)  # Multiple spaces/tabs -> single space
        
        # Remove common Confluence artifacts
        content = re.sub(r'\[Edit this page\].*?\n', '', content)
        content = re.sub(r'Â\xa0', ' ', content)  # Non-breaking spaces
        
        return content.strip()
    
    def _parse_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """Parse Confluence date string to datetime object."""
        if not date_str:
            return None
        
        try:
            # Confluence typically uses ISO format
            if 'T' in date_str:
                return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            else:
                return datetime.fromisoformat(date_str)
        except:
            return None
    
    def get_capabilities(self) -> Dict[str, Any]:
        """Return information about this adapter's capabilities."""
        return {
            'source_type': self.get_source_type(),
            'status': 'implemented',
            'features': [
                'space_crawling',
                'page_retrieval',
                'content_extraction',
                'metadata_extraction',
                'search_functionality',
                'conditional_chunking',
                'html_to_text_conversion',
                'label_extraction'
            ],
            'supported_inputs': [
                'space_key',
                'page_id', 
                'search_query',
                'page_url',
                'dict_config'
            ],
            'authentication_methods': [
                'username_api_token',
                'bearer_token'
            ],
            'configuration_options': [
                'confluence_url',
                'username',
                'api_token',
                'token',
                'embedding_model',
                'include_attachments',
                'max_pages'
            ],
            'embedding_model': self.embedding_model,
            'max_pages': self.max_pages
        }
    
    def cleanup(self) -> None:
        """Optional cleanup method."""
        if self.confluence_client:
            # Close any persistent connections if needed
            self.confluence_client = None 