import argparse
import os
import sys
import time

import db
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
    Parses command line arguments to support 'insert' and 'search' commands.
    Expected forms are:
    - python vsearch.py insert <path-to-code> [languages]
    - python vsearch.py search <path-to-code> <query>

    Returns:
        args (Namespace): An argparse.Namespace object containing the arguments
        command (str): The command specified ('insert' or 'search').
    """
    # Create the main parser
    parser = argparse.ArgumentParser(description='Process "insert" or "search" commands for code files.')
    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # Create the parser for the "insert" command
    parser_insert = subparsers.add_parser('insert', help='Insert code files into the database.')
    parser_insert.add_argument('path_to_code', type=str, help='Path to the directory where code files are located.')
    parser_insert.add_argument('languages', nargs='*',
                               help='Optional list of programming languages to filter the search.')

    # Create the parser for the "search" command
    parser_search = subparsers.add_parser('search', help='Search for code files in the database.')
    parser_search.add_argument('path_to_code', type=str, help='Path to the directory where code files are located.')
    parser_search.add_argument('query', type=str, help='Search query.')

    # Parse the command line arguments
    args = parser.parse_args()

    # command and path are always mandatory
    if args.command is None:
        parser.print_help()
        sys.exit(1)
    if not os.path.isdir(args.path_to_code):
        print(f"Error: The path {args.path_to_code} is not a directory.")
        sys.exit(1)

    if args.command == 'index':
        # Validate languages
        if args.languages:
            for language in args.languages:
                if language not in LANGUAGES_BY_EXTENSION.values():
                    print(f"Error: Unrecognized language {language}")
                    print(f"Recognized languages: {', '.join(LANGUAGES_BY_EXTENSION.values())}")
                    sys.exit(1)
    else:
        assert args.command == 'search'
        if not args.query:
            print(f"Error: The search query cannot be empty.")
            sys.exit(1)

    return args


def index(args):
    # Recursively walk through the directory to find code files
    languages_recognized = set()
    for root, dirs, files in os.walk(args.path_to_code):
        for file in files:
            full_path = os.path.join(root, file)
            language = infer_language_from_extension(full_path)
            if not language or (args.languages and language not in args.languages):
                continue
            languages_recognized.add(language)
            print(full_path)
            with open(full_path, 'r', encoding='utf-8') as file1:
                code = file1.read()
            chunks = combine_chunks(chunkify_code(code, language))
            start_time = time.time()
            encoded_chunks = [encode(chunk) for chunk in chunks]
            print(f'  encoding {len(chunks)} chunks took {time.time() - start_time:.2f}s')
            start_time = time.time()
            db.insert_embeddings(full_path, chunks, encoded_chunks)
            print(f'  inserting {len(chunks)} chunks took {time.time() - start_time:.2f}s')


def search(args):
    encoded_query = encode(args.query)
    for result in db.search(encoded_query):
        print(f"# {result['path']} #")
        print(result['chunk'])


if __name__ == '__main__':
    args = parse_arguments()
    if args.command == 'index':
        index(args)
    else:
        assert args.command == 'search'
        search(args)
