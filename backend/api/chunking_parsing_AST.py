import os
import logging
from typing import List, Dict, Optional
from tree_sitter import Language, Parser
from langchain.schema import Document

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Supported extensions and their corresponding Tree-sitter languages
EXTENSION_LANGUAGE_MAP = {
    ".py": "python",
    ".java": "java",
    ".js": "javascript",
    ".ts": "typescript",
    ".cpp": "cpp",
    ".h": "cpp",
    ".tsx": "typescript",
    ".jsx": "javascript",
}

IGNORED_DIRS = {'node_modules', 'venv', 'env', 'dist', 'build', '.git', '__pycache__', '.next', '.vscode', 'vendor'}

class TreeSitterParser:
    def __init__(self, language: str):
        self.language = language
        self.parser = Parser()
        self.parser.set_language(Language("build/my-languages.so", language))

    def parse_code(self, code: str):
        """Parses a code file using Tree-sitter."""
        return self.parser.parse(bytes(code, "utf-8"))

    def extract_chunks(self, tree, code: str, file_path: str) -> List[Dict]:
        """Extract classes, methods, and comments."""
        chunks = []
        root = tree.root_node

        # Module-level docstring extraction
        module_docstring = root.children[0] if root.children and root.children[0].type == "string" else None
        if module_docstring:
            chunks.append({
                "type": "module_docstring",
                "content": code[module_docstring.start_byte:module_docstring.end_byte],
                "start_line": module_docstring.start_point[0] + 1,
                "end_line": module_docstring.end_point[0] + 1,
                "path": file_path
            })

        for child in root.children:
            if child.type == "class_definition":
                class_name = child.child_by_field_name("name").text.decode("utf-8")
                chunks.append({
                    "type": "class",
                    "name": class_name,
                    "content": code[child.start_byte:child.end_byte],
                    "start_line": child.start_point[0] + 1,
                    "end_line": child.end_point[0] + 1,
                    "path": file_path
                })
            elif child.type == "function_definition":
                function_name = child.child_by_field_name("name").text.decode("utf-8")
                chunks.append({
                    "type": "method",
                    "name": function_name,
                    "content": code[child.start_byte:child.end_byte],
                    "start_line": child.start_point[0] + 1,
                    "end_line": child.end_point[0] + 1,
                    "path": file_path
                })

        return chunks

def get_file_content(file_path: str, repo_path: str) -> Optional[Dict[str, str]]:
    """Get content of a single file."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Use relative path for better metadata
        rel_path = os.path.relpath(file_path, repo_path)
        return {
            "name": rel_path,
            "content": content
        }
    except Exception as e:
        logger.error(f"Error reading file {file_path}: {str(e)}")
        return None

def get_main_files_content(repo_path: str) -> List[Document]:
    """Extract content of supported code files from a repository."""
    files_content = []

    try:
        for root, _, files in os.walk(repo_path):
            # Skip ignored directories
            if any(ignored_dir in root for ignored_dir in IGNORED_DIRS):
                continue

            for file in files:
                file_path = os.path.join(root, file)
                extension = os.path.splitext(file)[1]
                language = EXTENSION_LANGUAGE_MAP.get(extension)

                if language:
                    logger.info(f"Processing file: {file_path}")
                    file_content = get_file_content(file_path, repo_path)

                    if file_content:
                        parser = TreeSitterParser(language)
                        tree = parser.parse_code(file_content["content"])
                        extracted_chunks = parser.extract_chunks(tree, file_content["content"], file_path)

                        for chunk in extracted_chunks:
                            document = Document(
                                page_content=chunk["content"],
                                metadata={
                                    "type": chunk["type"],
                                    "name": chunk.get("name", ""),
                                    "path": chunk["path"],
                                    "start_line": chunk["start_line"],
                                    "end_line": chunk["end_line"]
                                }
                            )
                            files_content.append(document)

    except Exception as e:
        logger.error(f"Error processing repository: {str(e)}")

    return files_content
