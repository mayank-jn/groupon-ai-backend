#!/usr/bin/env python3
import os
from dotenv import load_dotenv
from sources.confluence.adapter import ConfluenceAdapter

load_dotenv()

config = {
    'confluence_url': os.getenv('CONFLUENCE_URL'),
    'username': os.getenv('CONFLUENCE_USERNAME'),
    'api_token': os.getenv('CONFLUENCE_API_TOKEN'),
    'max_pages': 5
}

adapter = ConfluenceAdapter(config)
if adapter.initialize():
    print('=== Available Spaces ===')
    spaces_response = adapter.confluence_client.get_all_spaces(limit=10)
    print(f'Spaces response type: {type(spaces_response)}')
    print(f'Spaces response keys: {spaces_response.keys() if isinstance(spaces_response, dict) else "Not a dict"}')
    
    # Handle the API response format
    if isinstance(spaces_response, dict) and 'results' in spaces_response:
        spaces = spaces_response['results']
    else:
        spaces = spaces_response
    
    print(f'Found {len(spaces)} spaces:')
    for i, space in enumerate(spaces):
        space_key = space.get('key', 'Unknown')
        space_name = space.get('name', 'Unknown')
        print(f'{i+1}. Space: {space_key} - {space_name}')
    
    if spaces:
        # Try the first space
        first_space = spaces[0]
        space_key = first_space.get('key')
        print(f'\n=== Testing with space: {space_key} ===')
        
        try:
            # Get pages from the space
            pages = adapter._get_space_pages(space_key, max_pages=3)
            print(f'Found {len(pages)} pages in space')
            for page in pages:
                title = page.get('title', 'Unknown')
                page_id = page.get('id', 'Unknown')
                print(f'  Page: {title} (ID: {page_id})')
        except Exception as e:
            print(f'Error getting pages: {e}')
            
        # Try processing the space
        print(f'\n=== Processing space {space_key} ===')
        try:
            results = adapter.process_source({'space_key': space_key})
            print(f'Processed: {len(results)} content chunks')
            for result in results[:2]:
                print(f'  - {result.title}: {len(result.content)} chars')
        except Exception as e:
            print(f'Error processing space: {e}')
else:
    print('Failed to initialize adapter') 