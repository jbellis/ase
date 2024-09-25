from typing import List
import warnings
warnings.simplefilter("ignore", category=FutureWarning)
from tree_sitter_languages import get_parser


def chunkify_code(code: str, language: str) -> List[str]:
    """
    Splits code into semantically meaningful chunks using tree-sitter.
    """
    parser = get_parser(language)
    tree = parser.parse(bytes(code, "utf8"))

    chunks = []
    for node in tree.root_node.children:
        if node.type in ("function_definition", "method_definition", "function_declaration", "method_declaration"):
            chunks.append(code[node.start_byte:node.end_byte])
        elif node.type in ("class_definition", "class_declaration"):
            class_chunk = code[node.start_byte:node.end_byte]
            chunks.append(class_chunk)
            
            # Add methods as separate chunks
            for child in node.children:
                if child.type in ("method_definition", "method_declaration", "function_definition", "function_declaration"):
                    chunks.append(code[child.start_byte:child.end_byte])

    return chunks
