import argparse
import os
import sys

from chunking import chunkify_code, combine_chunks
from encoder import encode


LANGUAGES_BY_EXTENSION = {
    '.py': 'Python',
    '.js': 'JavaScript',
    '.java': 'Java',
    '.cpp': 'C++',
    '.chh': 'C++',
    '.c': 'C',
    '.rs': 'Rust',
}
def infer_language_from_extension(filename: str) -> str:
    """
    Infers programming language from the file extension.
    """
    _, ext = os.path.splitext(filename)
    return LANGUAGES_BY_EXTENSION.get(ext.lower())


def parse_arguments():
    """
    Parses command line arguments.  Expected form is

    python vsearch.py <path-to-code> [languages]

    Returns:
        args (Namespace): An argparse.Namespace object containing the arguments
        - path_to_code (str): The path to the directory where code files are located.
        - languages (list of str): Optional. A list of programming languages to filter the search.
    """
    # Create the parser
    parser = argparse.ArgumentParser(description='Search for code files in a given directory and chunkify them.')
    # Add the positional argument for the path to the code directory
    parser.add_argument('path_to_code', type=str, help='Path to the directory where code files are located.')
    # Add the optional argument for specifying languages
    parser.add_argument('languages', nargs='*', help='Optional list of programming languages to filter the search.')
    # Parse the command line arguments
    args = parser.parse_args()
    # Validate languages
    if args.languages:
        for language in args.languages:
            if language not in LANGUAGES_BY_EXTENSION.values():
                print(f"Error: Unrecognized language {language}")
                print(f"Recognized languages: {', '.join(LANGUAGES_BY_EXTENSION.values())}")
                sys.exit(1)
    # validate path
    if not os.path.isdir(args.path_to_code):
        print(f"Error: The path {args.path_to_code} is not a directory.")
        sys.exit(1)
    return args


if __name__ == '__main__':
    args = parse_arguments()

    # Recursively walk through the directory to find code files
    languages_recognized = set()
    n_chunks = 0
    n_files = 0
    for root, dirs, files in os.walk(args.path_to_code):
        for file in files:
            full_path = os.path.join(root, file)
            language = infer_language_from_extension(full_path)
            if not language or (args.languages and language not in args.languages):
                continue
            n_files += 1
            languages_recognized.add(language)
            try:
                with open(full_path, 'r', encoding='utf-8') as file1:
                    code = file1.read()
                chunks = combine_chunks(chunkify_code(code, language))
                for chunk in chunks:
                    encode(chunk)
                n_chunks += len(chunks)
                print(f'\n# {full_path} #')
                for i, chunk in enumerate(chunks):
                    print(f'- Chunk {i + 1}:\n```\n{chunk}\n```\n\n')
            except Exception as e:
                print(f"Error processing file {full_path}: {e}")

    print("\n\n")
    print(f"Files processed: {n_files}")
    print(f"Recognized languages: {', '.join(languages_recognized)}")
    print(f"Total number of chunks: {n_chunks}")