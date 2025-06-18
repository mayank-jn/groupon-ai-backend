import os
import tempfile
import shutil
from pathlib import Path
from git import Repo
from sources.base.interfaces import SourceAdapter, SourceResult
from typing import Any, Dict, List, Optional
from github import Github  # PyGitHub
import re

# File types to process with enhanced support
ALLOWED_EXTENSIONS = {
    '.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.go', '.rs', '.cpp', '.c', '.h',
    '.md', '.txt', '.yml', '.yaml', '.json', '.xml', '.sql', '.sh', '.dockerfile'
}
IGNORE_DIRS = {'.git', 'node_modules', 'dist', 'build', 'venv', '__pycache__', '.next', 'target', 'vendor'}

# Size limits for better handling
MAX_FILE_SIZE = 100000  # 100KB max file size
MAX_CHUNK_SIZE = 4000   # 4KB max chunk size for embeddings
MIN_CHUNK_SIZE = 50     # Minimum chunk size to be useful

# Code patterns for intelligent chunking
FUNCTION_PATTERNS = {
    'python': r'(?:^|\n)(def\s+\w+.*?):',
    'javascript': r'(?:^|\n)((?:function\s+\w+|const\s+\w+\s*=.*?=>|\w+\s*:\s*function).*?{)',
    'typescript': r'(?:^|\n)((?:function\s+\w+|const\s+\w+\s*=.*?=>|\w+\s*:\s*function).*?{)',
    'java': r'(?:^|\n)(\s*(?:public|private|protected)?\s*(?:static)?\s*\w+\s+\w+\s*\([^)]*\)\s*{)',
    'go': r'(?:^|\n)(func\s+\w+.*?{)',
}

class GitHubSourceAdapter(SourceAdapter):
    """
    Enhanced GitHub source adapter for world-class semantic search.
    Features intelligent chunking, semantic metadata extraction, and optimized content processing.
    """
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        # Get GitHub token from config or environment
        self.github_token = (config or {}).get('github_token') or os.getenv('GITHUB_TOKEN')
        if not self.github_token:
            raise ValueError("GitHub token not found. Set GITHUB_TOKEN env var or pass in config.")
        # Initialize PyGitHub client
        self.gh_client = Github(self.github_token)

    def get_source_type(self) -> str:
        """Return the type of this source adapter."""
        return "github"

    def initialize(self) -> bool:
        """Initialize the adapter (e.g., check credentials, setup)."""
        try:
            user = self.gh_client.get_user().login
            print(f"✅ GitHub adapter initialized for user: {user}")
            return True
        except Exception as e:
            print(f"❌ GitHub authentication failed: {e}")
            return False

    def validate_input(self, source_input: Any) -> bool:
        """Validate that the input is a valid GitHub repo URL or identifier."""
        if not isinstance(source_input, str):
            return False
        return source_input.startswith('https://github.com/') or '/' in source_input

    def process_source(self, source_input: Any, **kwargs) -> List[SourceResult]:
        """
        Enhanced processing with intelligent chunking and semantic optimization.
        """
        repo_url = source_input
        temp_dir = tempfile.mkdtemp(prefix="ghrepo_")
        results = []
        
        try:
            print(f"🔄 Cloning {repo_url} to {temp_dir}")
            # Clone the repo
            Repo.clone_from(repo_url, temp_dir)
            
            # Extract repository metadata
            repo_metadata = self._extract_repo_metadata(repo_url, temp_dir)
            
            # Walk through the repo with intelligent processing
            for root, dirs, files in os.walk(temp_dir):
                # Skip ignored directories
                dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
                
                for file in files:
                    file_path = os.path.join(root, file)
                    rel_path = os.path.relpath(file_path, temp_dir)
                    ext = Path(file).suffix.lower()
                    
                    # Skip files with unallowed extensions
                    if ext not in ALLOWED_EXTENSIONS:
                        continue
                    
                    try:
                        # Process file with intelligent chunking
                        file_results = self._process_file_intelligently(
                            file_path, rel_path, repo_metadata
                        )
                        results.extend(file_results)
                        
                    except Exception as e:
                        print(f"⚠️  Error processing file {file_path}: {e}")
                        continue
            
            print(f"✅ Processed {len(results)} chunks from {repo_metadata['repo_full_name']}")
            return results
            
        except Exception as e:
            print(f"❌ Error processing repo {repo_url}: {e}")
            raise
        finally:
            # Cleanup temp directory
            shutil.rmtree(temp_dir)

    def _extract_repo_metadata(self, repo_url: str, temp_dir: str) -> Dict[str, Any]:
        """Extract comprehensive repository metadata."""
        # Extract full repo path from URL
        url_parts = repo_url.rstrip('/').replace('.git', '').split('/')
        if len(url_parts) >= 2:
            repo_full_name = f"{url_parts[-2]}/{url_parts[-1]}"
            owner = url_parts[-2]
            repo_name = url_parts[-1]
        else:
            repo_full_name = repo_url.rstrip('/').split('/')[-1].replace('.git', '')
            owner = "unknown"
            repo_name = repo_full_name

        # Try to get additional metadata from GitHub API
        try:
            gh_repo = self.gh_client.get_repo(repo_full_name)
            description = gh_repo.description or ""
            topics = gh_repo.get_topics()
            language = gh_repo.language or "unknown"
            stars = gh_repo.stargazers_count
        except:
            description = ""
            topics = []
            language = "unknown"
            stars = 0

        # Analyze repository structure
        tech_stack = self._analyze_tech_stack(temp_dir)
        
        return {
            "repo_full_name": repo_full_name,
            "owner": owner,
            "repo_name": repo_name,
            "description": description,
            "topics": topics,
            "primary_language": language,
            "stars": stars,
            "tech_stack": tech_stack
        }

    def _analyze_tech_stack(self, repo_dir: str) -> List[str]:
        """Analyze repository to determine technology stack."""
        tech_indicators = {
            'react': ['package.json', 'jsx', 'tsx'],
            'vue': ['vue.config.js', '.vue'],
            'angular': ['angular.json', '.component.ts'],
            'python': ['requirements.txt', 'setup.py', 'pyproject.toml'],
            'node': ['package.json', 'node_modules'],
            'docker': ['Dockerfile', 'docker-compose.yml'],
            'kubernetes': ['.yml', '.yaml', 'k8s'],
            'fastapi': ['fastapi', 'uvicorn'],
            'django': ['manage.py', 'settings.py'],
            'flask': ['app.py', 'flask'],
            'nextjs': ['next.config.js', '.next'],
            'typescript': ['.ts', '.tsx'],
            'javascript': ['.js', '.jsx']
        }
        
        detected_tech = []
        for tech, indicators in tech_indicators.items():
            for indicator in indicators:
                for root, dirs, files in os.walk(repo_dir):
                    if any(indicator in f for f in files) or any(indicator in d for d in dirs):
                        detected_tech.append(tech)
                        break
        
        return list(set(detected_tech))

    def _process_file_intelligently(self, file_path: str, rel_path: str, repo_metadata: Dict) -> List[SourceResult]:
        """Process a single file with intelligent chunking and semantic optimization."""
        try:
            # Check file size first
            file_size = os.path.getsize(file_path)
            if file_size > MAX_FILE_SIZE:
                print(f"⚠️  Skipping large file {rel_path} ({file_size} bytes)")
                return []
            
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
        except:
            return []

        if not content.strip() or len(content) < MIN_CHUNK_SIZE:
            return []

        ext = Path(file_path).suffix.lower()
        language = self._get_language(ext)
        file_name = os.path.basename(file_path)
        
        # Create base metadata
        base_metadata = {
            **repo_metadata,
            "repo": repo_metadata["repo_full_name"],
            "path": rel_path,
            "language": language,
            "type": "file",
            "name": file_name,
            "source_type": "github",
            "file_extension": ext,
            "file_size": len(content),
            "tech_stack": repo_metadata.get("tech_stack", [])
        }

        # Intelligent chunking based on file type
        if language in ['python', 'javascript', 'typescript', 'java', 'go']:
            return self._chunk_code_file(content, base_metadata)
        elif ext in ['.md', '.txt']:
            return self._chunk_documentation(content, base_metadata)
        elif ext in ['.json', '.yml', '.yaml']:
            return self._chunk_config_file(content, base_metadata)
        else:
            # Default chunking for other files
            return self._chunk_generic(content, base_metadata)

    def _chunk_code_file(self, content: str, metadata: Dict) -> List[SourceResult]:
        """Intelligently chunk code files by functions, classes, and logical blocks."""
        results = []
        language = metadata.get('language', '')
        
        # Try to split by functions/methods
        if language in FUNCTION_PATTERNS:
            pattern = FUNCTION_PATTERNS[language]
            matches = list(re.finditer(pattern, content, re.MULTILINE))
            
            if matches:
                # Process function-based chunks
                for i, match in enumerate(matches):
                    start_pos = match.start()
                    end_pos = matches[i + 1].start() if i + 1 < len(matches) else len(content)
                    
                    chunk_content = content[start_pos:end_pos].strip()
                    if len(chunk_content) < MIN_CHUNK_SIZE:  # Skip tiny chunks
                        continue
                    
                    # If chunk is too large, split it
                    if len(chunk_content) > MAX_CHUNK_SIZE:
                        # Split large functions into smaller chunks
                        sub_chunks = self._split_large_chunk(chunk_content, metadata, func_name)
                        results.extend(sub_chunks)
                        continue
                    
                    # Extract function/method name
                    func_match = re.search(r'(?:def|function|func)\s+(\w+)', chunk_content)
                    func_name = func_match.group(1) if func_match else f"block_{i}"
                    
                    # Enhanced metadata for code chunks
                    chunk_metadata = {
                        **metadata,
                        "chunk_type": "function",
                        "function_name": func_name,
                        "chunk_index": i,
                        "total_chunks": len(matches),
                        "chunk_size": len(chunk_content),
                        "semantic_tags": self._extract_semantic_tags(chunk_content, language)
                    }
                    
                    results.append(SourceResult(
                        content=chunk_content,
                        metadata=chunk_metadata,
                        source_type="github",
                        source_id=metadata["repo"],
                        title=f"{metadata['name']}::{func_name}"
                    ))
                
                return results
        
        # Fallback to size-based chunking for code
        return self._chunk_by_size(content, metadata, chunk_size=1000, overlap=100)

    def _chunk_documentation(self, content: str, metadata: Dict) -> List[SourceResult]:
        """Chunk documentation files by sections and headings."""
        results = []
        
        # Split by markdown headers
        sections = re.split(r'\n#+\s+', content)
        
        for i, section in enumerate(sections):
            if not section.strip() or len(section) < 100:
                continue
            
            # Extract section title
            lines = section.split('\n')
            title = lines[0].strip() if lines else f"section_{i}"
            
            chunk_metadata = {
                **metadata,
                "chunk_type": "documentation_section",
                "section_title": title,
                "chunk_index": i,
                "total_chunks": len(sections),
                "semantic_tags": self._extract_semantic_tags(section, "markdown")
            }
            
            results.append(SourceResult(
                content=section.strip(),
                metadata=chunk_metadata,
                source_type="github",
                source_id=metadata["repo"],
                title=f"{metadata['name']}::{title}"
            ))
        
        return results if results else self._chunk_by_size(content, metadata)

    def _chunk_config_file(self, content: str, metadata: Dict) -> List[SourceResult]:
        """Handle configuration files as single semantic units."""
        # Configuration files are usually best kept whole for context
        chunk_metadata = {
            **metadata,
            "chunk_type": "configuration",
            "semantic_tags": self._extract_config_tags(content, metadata.get('file_extension', ''))
        }
        
        return [SourceResult(
            content=content,
            metadata=chunk_metadata,
            source_type="github",
            source_id=metadata["repo"],
            title=metadata["name"]
        )]

    def _chunk_generic(self, content: str, metadata: Dict) -> List[SourceResult]:
        """Generic chunking for other file types."""
        return self._chunk_by_size(content, metadata, chunk_size=800, overlap=50)

    def _chunk_by_size(self, content: str, metadata: Dict, chunk_size: int = 1000, overlap: int = 100) -> List[SourceResult]:
        """Chunk content by size with overlap."""
        # Respect the maximum chunk size limit
        chunk_size = min(chunk_size, MAX_CHUNK_SIZE)
        overlap = min(overlap, chunk_size // 4)  # Overlap should be max 25% of chunk size
        
        results = []
        
        for i in range(0, len(content), chunk_size - overlap):
            chunk = content[i:i + chunk_size]
            if not chunk.strip() or len(chunk) < MIN_CHUNK_SIZE:
                continue
            
            chunk_metadata = {
                **metadata,
                "chunk_type": "size_based",
                "chunk_index": i // (chunk_size - overlap),
                "chunk_size": len(chunk),
                "semantic_tags": self._extract_semantic_tags(chunk, metadata.get('language', ''))
            }
            
            results.append(SourceResult(
                content=chunk,
                metadata=chunk_metadata,
                source_type="github",
                source_id=metadata["repo"],
                title=f"{metadata['name']}::chunk_{i // (chunk_size - overlap)}"
            ))
        
        return results

    def _extract_semantic_tags(self, content: str, language: str) -> List[str]:
        """Extract semantic tags from content for better searchability."""
        tags = []
        content_lower = content.lower()
        
        # Programming concepts
        if 'api' in content_lower or 'endpoint' in content_lower:
            tags.append('api')
        if 'database' in content_lower or 'db' in content_lower or 'sql' in content_lower:
            tags.append('database')
        if 'auth' in content_lower or 'login' in content_lower or 'token' in content_lower:
            tags.append('authentication')
        if 'test' in content_lower or 'spec' in content_lower:
            tags.append('testing')
        if 'config' in content_lower or 'setting' in content_lower:
            tags.append('configuration')
        if 'error' in content_lower or 'exception' in content_lower:
            tags.append('error_handling')
        if 'async' in content_lower or 'await' in content_lower or 'promise' in content_lower:
            tags.append('async')
        if 'class' in content_lower or 'interface' in content_lower:
            tags.append('object_oriented')
        if 'import' in content_lower or 'require' in content_lower:
            tags.append('dependencies')
        
        # Add language-specific tags
        tags.append(language)
        
        return tags

    def _extract_config_tags(self, content: str, extension: str) -> List[str]:
        """Extract semantic tags from configuration files."""
        tags = ['configuration']
        content_lower = content.lower()
        
        if extension in ['.yml', '.yaml']:
            tags.append('yaml')
        elif extension == '.json':
            tags.append('json')
        
        # Configuration-specific concepts
        if 'port' in content_lower or 'host' in content_lower:
            tags.append('networking')
        if 'database' in content_lower or 'db' in content_lower:
            tags.append('database')
        if 'env' in content_lower or 'environment' in content_lower:
            tags.append('environment')
        if 'docker' in content_lower:
            tags.append('docker')
        if 'kubernetes' in content_lower or 'k8s' in content_lower:
            tags.append('kubernetes')
        
        return tags

    def _get_language(self, ext: str) -> str:
        """Get language name from file extension with enhanced mapping."""
        language_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.jsx': 'javascript',
            '.tsx': 'typescript',
            '.java': 'java',
            '.go': 'go',
            '.rs': 'rust',
            '.cpp': 'cpp',
            '.c': 'c',
            '.h': 'c',
            '.md': 'markdown',
            '.txt': 'text',
            '.yml': 'yaml',
            '.yaml': 'yaml',
            '.json': 'json',
            '.xml': 'xml',
            '.sql': 'sql',
            '.sh': 'shell',
            '.dockerfile': 'docker'
        }
        return language_map.get(ext, 'text')

    def get_capabilities(self) -> Dict[str, Any]:
        """Return enhanced information about this adapter's capabilities."""
        return {
            "source_type": "github",
            "supports_code": True,
            "supports_markdown": True,
            "supports_intelligent_chunking": True,
            "supports_semantic_tagging": True,
            "supports_function_extraction": True,
            "filters": ["repo", "path", "language", "type", "name", "function_name", "section_title", "semantic_tags", "tech_stack"],
            "chunk_types": ["function", "documentation_section", "configuration", "size_based"],
            "languages": list(FUNCTION_PATTERNS.keys()) + ["markdown", "yaml", "json", "text"]
        }

    def _split_large_chunk(self, content: str, metadata: Dict, identifier: str) -> List[SourceResult]:
        """Split a large chunk into smaller ones while preserving semantic meaning."""
        results = []
        chunk_size = MAX_CHUNK_SIZE - 200  # Leave some buffer
        overlap = 100
        
        for i in range(0, len(content), chunk_size - overlap):
            chunk = content[i:i + chunk_size]
            if not chunk.strip() or len(chunk) < MIN_CHUNK_SIZE:
                continue
            
            chunk_metadata = {
                **metadata,
                "chunk_type": "large_split",
                "original_identifier": identifier,
                "chunk_index": i // (chunk_size - overlap),
                "chunk_size": len(chunk),
                "semantic_tags": self._extract_semantic_tags(chunk, metadata.get('language', ''))
            }
            
            results.append(SourceResult(
                content=chunk,
                metadata=chunk_metadata,
                source_type="github",
                source_id=metadata["repo"],
                title=f"{metadata['name']}::{identifier}::part_{i // (chunk_size - overlap)}"
            ))
        
        return results

    def _chunk_config_file(self, content: str, metadata: Dict) -> List[SourceResult]:
        """Handle configuration files as single semantic units."""
        # Configuration files are usually best kept whole for context
        chunk_metadata = {
            **metadata,
            "chunk_type": "configuration",
            "semantic_tags": self._extract_config_tags(content, metadata.get('file_extension', ''))
        }
        
        return [SourceResult(
            content=content,
            metadata=chunk_metadata,
            source_type="github",
            source_id=metadata["repo"],
            title=metadata["name"]
        )] 