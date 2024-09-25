import os
from typing import List, Tuple
from tree_sitter import Language, Parser
from tree_sitter_languages import get_language, get_parser

def get_tree_sitter_parser(language: str) -> Tuple[Language, Parser]:
    """
    Get the appropriate tree-sitter language and parser for the given language.
    """
    lang = get_language(language)
    parser = get_parser(language)
    return lang, parser


def chunkify_code(code: str, language: str) -> List[str]:
    """
    Splits code into semantically meaningful chunks using tree-sitter.
    """
    lang, parser = get_tree_sitter_parser(language)
    tree = parser.parse(bytes(code, "utf8"))

    chunks = []
    for node in tree.root_node.children:
        if node.type in ("function_definition", "method_definition"):
            chunks.append(code[node.start_byte:node.end_byte])
        elif node.type == "class_definition":
            class_chunk = code[node.start_byte:node.end_byte]
            class_lines = class_chunk.split('\n')
            
            # Find the end of class declaration and fields
            end_of_fields = next((i for i, line in enumerate(class_lines) if "def " in line), len(class_lines))
            
            # Add class declaration and fields as one chunk
            chunks.append('\n'.join(class_lines[:end_of_fields]))
            
            # Add methods as separate chunks
            for method_node in node.children:
                if method_node.type == "method_definition":
                    chunks.append(code[method_node.start_byte:method_node.end_byte])

    return chunks
