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
    
    def traverse(node):
        if node.type in ("class_declaration", "interface_declaration", "enum_declaration"):
            # For classes, interfaces, and enums, we'll chunk their contents separately
            class_chunk = code[node.start_byte:node.end_byte]
            chunks.append(class_chunk)
            for child in node.children:
                traverse(child)
        elif node.type in ("function_definition", "method_definition", "function_declaration", "method_declaration", "constructor_declaration"):
            # TODO for C-like languages we only want to capture definitions, not declarations
            method_chunk = code[node.start_byte:node.end_byte]
            chunks.append(method_chunk)
        else:
            # For other node types, continue traversing
            for child in node.children:
                traverse(child)

    traverse(tree.root_node)
    
    return chunks
