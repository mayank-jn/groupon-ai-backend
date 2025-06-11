#!/usr/bin/env python3
"""
Test script to demonstrate conditional chunking functionality.
This script shows how documents are processed differently based on their size.
"""

from ingest.pdf_ingest import chunk_text_conditionally, count_tokens

def test_conditional_chunking():
    # Test case 1: Small document that shouldn't be chunked
    small_doc = """
    This is a small document that contains basic information about our system.
    It has a few paragraphs but should remain as a single chunk since it's
    well under the token limit for embeddings.
    
    The system will detect that this document is small enough to be embedded
    as a single piece, preserving all context relationships.
    """
    
    # Test case 2: Large document that should be chunked
    large_doc = "This is a large document. " * 1000  # Repeat to make it large
    
    print("=== Conditional Chunking Test ===\n")
    
    # Test small document
    small_tokens = count_tokens(small_doc)
    small_chunks = chunk_text_conditionally(small_doc)
    
    print(f"Small Document:")
    print(f"  Token count: {small_tokens}")
    print(f"  Number of chunks: {len(small_chunks)}")
    print(f"  Processing: {'Single embedding' if len(small_chunks) == 1 else 'Chunked'}")
    print()
    
    # Test large document
    large_tokens = count_tokens(large_doc)
    large_chunks = chunk_text_conditionally(large_doc)
    
    print(f"Large Document:")
    print(f"  Token count: {large_tokens}")
    print(f"  Number of chunks: {len(large_chunks)}")
    print(f"  Processing: {'Single embedding' if len(large_chunks) == 1 else 'Chunked'}")
    print()
    
    print("=== Token Limit Info ===")
    print(f"Embedding token limit: 8000")
    print(f"Small doc exceeds limit: {small_tokens > 8000}")
    print(f"Large doc exceeds limit: {large_tokens > 8000}")

if __name__ == "__main__":
    test_conditional_chunking() 