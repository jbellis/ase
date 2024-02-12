import argparse
import os
import sys
from itertools import groupby
from operator import itemgetter

import db
from chunking import chunkify_code, combine_chunks
from util import hexdigest

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
    Parses command line arguments to support 'index' and 'search' commands.
    Expected forms are:
    - python vsearch.py index <path-to-code> [--collection collection_name] [languages]
    - python vsearch.py search <path-to-code> [--collection collection_name] <query> [--files-only]

    Returns:
        args (Namespace): An argparse.Namespace object containing the arguments
        command (str): The command specified ('index' or 'search').
    """
    # Create the main parser
    parser = argparse.ArgumentParser(description='Process "index" or "search" commands for code files.')
    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # Create the parser for the "index" command
    parser_index = subparsers.add_parser('index', help='Index code files into the database.')
    parser_index.add_argument('path_to_code', type=str, help='Path to the directory where code files are located.')
    parser_index.add_argument('--collection', type=str, help='Name of the collection to use. Defaults to directory name.')
    parser_index.add_argument('languages', nargs='*',
                               help='Optional list of programming languages to filter the search.')

    # Create the parser for the "search" command
    parser_search = subparsers.add_parser('search', help='Search for code files in the database.')
    parser_search.add_argument('path_to_code', type=str, help='Path to the directory where code files are located.')
    parser_search.add_argument('--collection', type=str, help='Name of the collection to use. Defaults to directory name.')
    parser_search.add_argument('query', type=str, help='Search query.')
    parser_search.add_argument('--files-only', action='store_true', help='Limit search to files only.')

    # Parse the command line arguments
    args = parser.parse_args()

    # command and path are always mandatory
    if args.command is None:
        parser.print_help()
        sys.exit(1)
    if not os.path.isdir(args.path_to_code):
        print(f"Error: The path {args.path_to_code} is not a directory.")
        sys.exit(1)
    # collection name defaults to directory name
    if not args.collection:
        args.collection = os.path.basename(args.path_to_code)

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
    known_files_by_path = {file_doc['path']: file_doc
                           for file_doc in db.load_hashes()}
    real_root = os.path.realpath(args.path_to_code)
    n_unchanged = 0
    # Recursively walk through the directory to find code files
    for root, dirs, files in os.walk(real_root):
        for file in files:
            full_path = os.path.join(root, file)

            language = infer_language_from_extension(full_path)
            if not language or (args.languages and language not in args.languages):
                continue

            file_doc = known_files_by_path.get(full_path)
            if file_doc:
                if hexdigest(full_path) == file_doc['hash']:
                    n_unchanged += 1
                    continue
                else:
                    db.delete(file_doc)
            file_id = file_doc['_id'] if file_doc else None

            from encoder import encode
            sys.stdout.write(file)
            code = open(full_path, 'r', encoding='utf-8').read()
            chunks = combine_chunks(chunkify_code(code, language))
            sys.stdout.write(f' {len(chunks)} chunks')
            encoded_chunks = [encode(chunk) for chunk in chunks]
            sys.stdout.write(f' (encoded)')
            db.insert(file_id, full_path, chunks, encoded_chunks)
            print(f' (inserted)')
    if n_unchanged:
        print(f"{n_unchanged} files unchanged")


def search(args):
    encoded_query = encode(args.query)
    result_sorted = sorted(db.search(encoded_query), key=itemgetter('path'))
    results_by_path = {key: [item['chunk'] for item in group]
                       for key, group in groupby(result_sorted, key=itemgetter('path'))}
    for path, chunks in results_by_path.items():
        if args.files_only:
            print(path)
        else:
            print(f"# {path} #")
            print('\n...\n'.join(chunks))


if __name__ == '__main__':
    args = parse_arguments()
    db.connect(args.collection)
    if args.command == 'index':
        index(args)
    else:
        assert args.command == 'search'
        search(args)
