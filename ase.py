import argparse
import os
import sys
from itertools import groupby
from operator import itemgetter

from tqdm import tqdm

import db
from chunking import chunkify_code
from util import hexdigest, get_indexable_files, infer_language, validate_language

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
    parser_index.add_argument('path_to_code', type=str, nargs='?', default=os.getcwd(),
                              help='Path to the directory where code files are located. Defaults to current working directory.')
    parser_index.add_argument('--collection', type=str, help='Name of the collection to use. Defaults to directory name.')
    # Adjusted parser_index to make languages an optional argument
    parser_index.add_argument('--languages', nargs='*',
                              help='Optional list of programming languages to filter the search.')

    # Create the parser for the "search" command
    parser_search = subparsers.add_parser('search', help='Search for code files in the database.')
    parser_search.add_argument('path_to_code', type=str, nargs='?', default=os.getcwd(),
                               help='Path to the directory where code files are located. Defaults to current working directory.')
    parser_search.add_argument('query', type=str, help='Search query.')
    parser_search.add_argument('--collection', type=str, help='Name of the collection to use. Defaults to directory name.')
    parser_search.add_argument('--files', action='store_true', help='Output entire file contents instead of just matching chunks.')
    parser_search.add_argument('--limit', type=int, help='Number of search results to include.')

    # Parse the command line arguments
    args = parser.parse_args()

    # command is always mandatory
    if args.command is None:
        parser.print_help()
        sys.exit(1)
    # Ensure path_to_code is a valid directory
    args.path_to_code = os.path.abspath(args.path_to_code)
    if not os.path.isdir(args.path_to_code):
        print(f"Error: The path {args.path_to_code} is not a directory.")
        sys.exit(1)
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
                validate_language(language)
    else:
        assert args.command == 'search'
        if not args.query:
            print(f"Error: The search query cannot be empty.")
            sys.exit(1)

    return args


def index(args):
    known_files_by_path = {file_doc['path']: file_doc
                           for file_doc in db.load_hashes()}
    n_unchanged = 0

    print('Scanning for files to index')
    all_paths = get_indexable_files(args.path_to_code, args.languages)
    
    # Prune list to changed or new files
    paths_to_index = []
    for full_path in tqdm(all_paths, desc="Checking file changes", unit="file"):
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
    for full_path in tqdm(paths_to_index, desc="Indexing files", unit="file"):
        file_doc = known_files_by_path.get(full_path)
        file_id = file_doc['_id'] if file_doc else None

        from encoder import encode
        contents = open(full_path, 'r', encoding='utf-8').read()
        language = infer_language(full_path)
        chunks = chunkify_code(contents, language)
        encoded_chunks = encode(chunks)
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
