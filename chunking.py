from typing import List
import warnings

warnings.simplefilter("ignore", category=FutureWarning)
from tree_sitter_languages import get_parser


def chunkify_code(code: str, language: str) -> List[str]:
    """
    Splits code into semantically meaningful chunks using tree-sitter.
    """
    parser = get_parser(language)
    code_bytes = code.encode('utf-8')
    tree = parser.parse(code_bytes)

    chunks = []

    def is_definition(node):
        """Check if a node represents a definition rather than just a declaration."""
        if node.type.endswith("_definition"):
            return True
        if node.type in ("function_declaration", "method_declaration", "constructor_declaration"):
            # Check if the node has a body (compound_statement)
            return any(child.type == "block" for child in node.children)
        return False

    def byte_to_char_offset(byte_offset):
        return len(code_bytes[:byte_offset].decode('utf-8'))

    def traverse(node):
        if node.type in ("class_declaration", "interface_declaration", "enum_declaration"):
            # For classes, interfaces, and enums, we'll include the full declaration line and fields
            class_def_end = next((child.start_byte for child in node.children if child.type == "class_body"), node.end_byte)
            full_def = code[byte_to_char_offset(node.start_byte):byte_to_char_offset(class_def_end)].strip()
            class_fields = [full_def]
            class_body = next((child for child in node.children if child.type == "class_body"), None)
            if class_body:
                for child in class_body.children:
                    if child.type in ("field_declaration", "variable_declaration"):
                        field_chunk = code[byte_to_char_offset(child.start_byte):byte_to_char_offset(child.end_byte)].strip()
                        class_fields.append(field_chunk)
            if class_fields:
                chunks.append("\n".join(class_fields))
            # Continue traversing to handle nested classes and methods
            for child in node.children:
                traverse(child)
        elif node.type in ("function_definition", "method_definition", "function_declaration", "method_declaration",
                           "constructor_declaration"):
            if is_definition(node):
                method_chunk = code[byte_to_char_offset(node.start_byte):byte_to_char_offset(node.end_byte)]
                chunks.append(method_chunk)
        else:
            # For other node types, continue traversing
            for child in node.children:
                traverse(child)

    traverse(tree.root_node)

    return chunks
