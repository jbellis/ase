import hashlib
import os
import sys


def hexdigest(full_path):
    hash = hashlib.sha256()
    hash.update(open(full_path, 'rb').read())
    return hash.hexdigest()


def get_indexable_files(root, languages=None):
    """
    Returns a list of files that can be indexed based on their language.

    :param root: Path to the directory containing code files
    :param languages: Optional list of languages to filter by
    :return: List of full file paths that can be indexed
    """
    real_root = os.path.realpath(root)
    indexable_files = []

    for root, _, files in os.walk(real_root):
        for file in files:
            full_path = os.path.join(root, file)
            language = infer_language(full_path)
            if language and (not languages or language in languages):
                indexable_files.append(full_path)

    return indexable_files


LANGUAGES_BY_EXTENSION = {
    '.py': 'python',
    '.js': 'javascript',
    '.java': 'java',
    '.cpp': 'cpp',
    '.hpp': 'cpp',
    '.c': 'c',
    '.h': 'c',
    '.rs': 'rust',
    '.go': 'go',
    '.rb': 'ruby',
    '.php': 'php',
    '.ts': 'typescript',
    '.cs': 'c_sharp',
    '.swift': 'swift',
    '.kt': 'kotlin',
    '.scala': 'scala',
    '.lua': 'lua',
    '.sh': 'bash',
}

def infer_language(filename: str) -> str:
    """
    Infers programming language from the file extension.
    Returns the language name recognized by tree-sitter.
    """
    _, ext = os.path.splitext(filename)
    return LANGUAGES_BY_EXTENSION.get(ext.lower())


def validate_language(language):
    if language not in LANGUAGES_BY_EXTENSION.values():
        print(f"Error: Unrecognized language {language}")
        print(f"Recognized languages: {', '.join(LANGUAGES_BY_EXTENSION.values())}")
        print("Note: Language names are case-sensitive and should be lowercase.")
        sys.exit(1)
