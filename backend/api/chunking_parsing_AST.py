import os
import logging
from typing import List, Dict, Optional
from tree_sitter_languages import get_parser

# Configure logging
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {".py", ".java", ".js", ".ts", ".cpp", ".h", ".ipynb"}
IGNORED_EXTENSIONS = {
    ".pkl", ".npy", ".h5", ".bin", ".exe", ".dll", ".so", ".o", ".class", ".log", ".txt", 
    ".md", ".csv", ".json", ".xml", ".yaml", ".yml", ".lock"
}
IGNORED_DIRS = {"node_modules", "venv", "env", "dist", "build", ".git", "__pycache__", ".next", ".vscode", "vendor"}

class SimpleTreeSitterParser:
    def __init__(self, language: str):
        """
        Initialize the parser for the specified language using `tree_sitter_languages`.
        """
        self.language = language
        try:
            logger.info(f"Initializing parser for language: {language}")
            self.parser = get_parser(language)
            logger.debug(f"Parser for {language} initialized: {self.parser}")
        except Exception as e:
            logger.error(f"Error initializing parser for {language}: {str(e)}")
            raise ValueError(f"Error initializing parser for {language}: {str(e)}")

    def parse(self, code: str) -> List[Dict]:
        """
        Parse the given code to extract structured chunks (e.g., classes, methods, variables).
        Returns a list of extracted chunks with their type, content, and line ranges.
        """
        try:
            tree = self.parser.parse(bytes(code, "utf-8"))
            root = tree.root_node
        except Exception as e:
            logger.error(f"Error parsing code: {str(e)}")
            raise ValueError(f"Error parsing code: {str(e)}")

        chunks = []
        for child in root.children:
            logger.debug(f"Node Type: {child.type}, Start: {child.start_point}, End: {child.end_point}")

            # Extract recognized chunks
            if child.type in {"class", "class_declaration", "class_definition"}:
                chunks.append({
                    "type": "class",
                    "content": code[child.start_byte:child.end_byte],
                    "start_line": child.start_point[0] + 1,
                    "end_line": child.end_point[0] + 1,
                })
            elif child.type in {"function", "function_definition", "method", "method_declaration"}:
                chunks.append({
                    "type": "method",
                    "content": code[child.start_byte:child.end_byte],
                    "start_line": child.start_point[0] + 1,
                    "end_line": child.end_point[0] + 1,
                })
            elif child.type in {"variable_declaration", "declaration", "let_declaration", "const_declaration"}:
                chunks.append({
                    "type": "variable",
                    "content": code[child.start_byte:child.end_byte],
                    "start_line": child.start_point[0] + 1,
                    "end_line": child.end_point[0] + 1,
                })
            elif child.type in {"import_statement", "import"}:
                chunks.append({
                    "type": "import",
                    "content": code[child.start_byte:child.end_byte],
                    "start_line": child.start_point[0] + 1,
                    "end_line": child.end_point[0] + 1,
                })
            elif child.type in {"export_statement", "export"}:
                chunks.append({
                    "type": "export",
                    "content": code[child.start_byte:child.end_byte],
                    "start_line": child.start_point[0] + 1,
                    "end_line": child.end_point[0] + 1,
                })
            else:
                logger.warning(f"Unrecognized node type: {child.type}")
        return chunks

def get_file_content(file_path: str) -> Optional[str]:
    """
    Read and return the content of a file. Returns None if reading fails.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        logger.error(f"Error reading file {file_path}: {str(e)}")
        return None

def parse_repo_store_all(repo_path: str) -> List[Dict]:
    """
    Parse the repository and store both parsed structured chunks and full file content.
    Returns a list of chunks, including parsed and raw content.
    """
    all_chunks = []

    for root, _, files in os.walk(repo_path):
        # Skip ignored directories
        if any(ignored_dir in root for ignored_dir in IGNORED_DIRS):
            continue

        for file in files:
            file_path = os.path.join(root, file)
            extension = os.path.splitext(file)[1]

            # Skip ignored file extensions
            if extension in IGNORED_EXTENSIONS:
                logger.warning(f"Skipping unsupported file type: {file_path}")
                continue

            # Process only supported extensions
            if extension in SUPPORTED_EXTENSIONS:
                language = {
                    ".py": "python",
                    ".ipynb": "python",
                    ".java": "java",
                    ".js": "javascript",
                    ".ts": "typescript",
                    ".cpp": "cpp",
                    ".h": "cpp",
                }.get(extension)

                try:
                    logger.info(f"Processing file: {file_path}")
                    code = get_file_content(file_path)
                    if not code:
                        logger.warning(f"No content found in {file_path}")
                        continue

                    # Attempt parsing and store structured chunks
                    parser = SimpleTreeSitterParser(language)
                    chunks = parser.parse(code)
                    all_chunks.extend(chunks)

                    # Also store the entire file content as a separate entry
                    all_chunks.append({
                        "type": "file",
                        "content": code,
                        "file_path": file_path
                    })
                except ValueError as ve:
                    logger.error(f"Language not supported or parsing error for {file_path}: {ve}")
                    all_chunks.append({
                        "type": "file",
                        "content": code,
                        "file_path": file_path
                    })
                except Exception as e:
                    logger.error(f"Unexpected error processing {file_path}: {str(e)}")
                    all_chunks.append({
                        "type": "file",
                        "content": code,
                        "file_path": file_path
                    })
            else:
                logger.warning(f"Unsupported file type: {file_path}")

    if not all_chunks:
        raise ValueError("No valid code chunks found in the repository.")

    return all_chunks
