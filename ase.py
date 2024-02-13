import argparse
import os
import sys
from itertools import groupby
from operator import itemgetter

from tqdm import tqdm

import db
from chunking import chunkify_code, combine_chunks
from util import hexdigest

LANGUAGES_BY_EXTENSION = {
    '.py': 'Python',
    '.js': 'JavaScript',
    '.java': 'Java',
    '.cpp': 'C++',
    '.hpp': 'C++',
    '.c': 'C',
    '.h': 'C',
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
    Parses command line arguments to support 'index' and 'search' commands with enhanced flexibility for specifying programming languages as an optional argument in the 'index' command. Expected forms are:
    - python codelocal.py index <path-to-code>
      [--collection collection_name]
      [--languages [language1 language2 ...]]
    - python codelocal.py search <path-to-code> <query>
      [--collection collection_name]
      [--files]
      [--limit number_of_results]

    Returns:
        An argparse.Namespace object containing the parsed arguments.
    """
    # Create the main parser
    parser = argparse.ArgumentParser(description='Process "index" or "search" commands for code files.')
    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # Create the parser for the "index" command
    parser_index = subparsers.add_parser('index', help='Index code files into the database.')
    parser_index.add_argument('path_to_code', type=str, help='Path to the directory where code files are located.')
    parser_index.add_argument('--collection', type=str, help='Name of the collection to use. Defaults to directory name.')
    # Adjusted parser_index to make languages an optional argument
    parser_index.add_argument('--languages', nargs='*',
                              help='Optional list of programming languages to filter the search.')

    # Create the parser for the "search" command
    parser_search = subparsers.add_parser('search', help='Search for code files in the database.')
    parser_search.add_argument('path_to_code', type=str, help='Path to the directory where code files are located.')
    parser_search.add_argument('query', type=str, help='Search query.')
    parser_search.add_argument('--collection', type=str, help='Name of the collection to use. Defaults to directory name.')
    parser_search.add_argument('--files', action='store_true', help='Output entire file contents instead of just matching chunks.')
    parser_search.add_argument('--limit', type=int, help='Number of search results to include.')

    # Parse the command line arguments
    args = parser.parse_args()

    # command and path are always mandatory
    if args.command is None:
        parser.print_help()
        sys.exit(1)
    if not os.path.isdir(args.path_to_code):
        print(f"Error: The path {args.path_to_code} is not a directory.")
        sys.exit(1)
    # strip off trailing slash, if present -- it confuses os.path.basename
    args.path_to_code = args.path_to_code.rstrip('/')
    # collection name defaults to directory name
    if not args.collection:
        # Remove non-alphanumeric characters from the directory name since we're going to use this
        # as a database table name
        basename = os.path.basename(args.path_to_code)
        args.collection = ''.join(c for c in basename if c.isalnum())

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

    print('Scanning for files to index')
    # Collect all files in the directory into a flat list
    all_paths = []
    for root, dirs, files in os.walk(real_root):
        for file in files:
            full_path = os.path.join(root, file)
            all_paths.append(full_path)
    # Prune list to changed or new files
    paths_to_index = []
    for full_path in tqdm(all_paths):
        language = infer_language_from_extension(full_path)
        if not language or (args.languages and language not in args.languages):
            continue
        file_doc = known_files_by_path.get(full_path)
        if file_doc:
            if hexdigest(full_path) == file_doc['hash']:
                n_unchanged += 1
                continue
            else:
                db.delete(file_doc['_id'])
        paths_to_index.append(full_path)

    # encode and store the interesting files
    print(f'Indexing {len(paths_to_index)} files ({n_unchanged} unchanged)')
    for full_path in tqdm(paths_to_index):
        file_doc = known_files_by_path.get(full_path)
        file_id = file_doc['_id'] if file_doc else None

        from encoder import encode
        contents = open(full_path, 'r', encoding='utf-8').read()
        chunks = combine_chunks(chunkify_code(contents, language))
        encoded_chunks = [encode(chunk) for chunk in chunks]
        db.insert(file_id, full_path, chunks, encoded_chunks)


def search(args):
    from encoder import encode
    encoded_query = encode(args.query)
    result_sorted = sorted(db.search(encoded_query), key=itemgetter('file_id'))
    results_by_file = sorted(((key, [item['chunk'] for item in group])
                             for key, group in groupby(result_sorted, key=itemgetter('file_id'))),
                             key=lambda kv: -len(kv[1]))
    if args.files:
        for file_id, _ in results_by_file:
            print('# {full_path} #')
            print(open(file_id, 'r', encoding='utf-8').read())
    else:
        for file_id, chunks in results_by_file:
            full_path = db.file_by_id(file_id)['path']
            print(f"# {full_path} #")
            print('\n...\n'.join(chunks))


if __name__ == '__main__':
    args = parse_arguments()
    db.init(args.collection)
    if args.command == 'index':
        index(args)
    else:
        assert args.command == 'search'
        search(args)
