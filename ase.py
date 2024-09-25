import argparse
import os
import sys
from pathlib import Path

from tqdm import tqdm

import db
from chunking import chunkify_code
from util import hexdigest, get_indexable_files, infer_language, validate_language


def relativize(full_path, base_path):
    """
    Convert a full path to a path relative to the base_path.
    
    Args:
        full_path (str): The full path to convert.
        base_path (str): The base path to make the full_path relative to.
    
    Returns:
        str: The relative path.
    """
    return str(Path(full_path).relative_to(base_path))

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
    parser_search.add_argument('-l', '--files-with-matches', action='store_true', help='Print only the names of files containing matches.')
    parser_search.add_argument('-m', '--max-count', type=int, default=5, help='Return a maximum of NUM matches (default: 5)', metavar='NUM')

    # Create the parser for the "debug-index" command
    parser_debug_index = subparsers.add_parser('debug-index', help='List all indexed files with their hexdigest.')
    parser_debug_index.add_argument('--collection', type=str, help='Name of the collection to use. Defaults to directory name.')
    parser_debug_index.add_argument('path_to_code', type=str, nargs='?', default=os.getcwd(),
                                    help='Path to the directory where code files are located. Defaults to current working directory.')

    # Create the parser for the "prune" command
    parser_prune = subparsers.add_parser('prune', help='Delete specified file(s) from the index.')
    parser_prune.add_argument('files', nargs='+', help='File(s) to delete from the index.')
    parser_prune.add_argument('path_to_code', type=str, nargs='?', default=os.getcwd(),
                              help='Path to the directory where code files are located. Defaults to current working directory.')
    parser_prune.add_argument('--collection', type=str, help='Name of the collection to use. Defaults to directory name.')

    # Create the parser for the "debug-chunks" command
    parser_debug_chunks = subparsers.add_parser('debug-chunks', help='List the DB chunks associated with a given file.')
    parser_debug_chunks.add_argument('file', type=str, help='File to list chunks for.')
    parser_debug_chunks.add_argument('path_to_code', type=str, nargs='?', default=os.getcwd(),
                                     help='Path to the directory where code files are located. Defaults to current working directory.')
    parser_debug_chunks.add_argument('--collection', type=str, help='Name of the collection to use. Defaults to directory name.')

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
        if args.command == 'search' and not args.query:
            print(f"Error: The search query cannot be empty.")
            sys.exit(1)

    return args


def debug_index(args):
    print(f"Listing indexed files for collection: {args.collection}")
    for file_doc in db.hashes_cursor():
        relative_path = relativize(file_doc['path'], args.path_to_code)
        print(f"{relative_path}: {file_doc['hash']}")


def index(args):
    known_files_by_path = {}
    for file_doc in tqdm(db.hashes_cursor(), desc="Loading known files from Astra", bar_format='{desc}: {n_fmt}'):
        known_files_by_path[file_doc['path']] = file_doc
    n_unchanged = 0

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

    if not paths_to_index:
        print('No new or changed files to index')
        return
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


from collections import defaultdict

def search(args):
    from encoder import encode
    encoded_query = encode([args.query])[0]
    results = db.search(encoded_query, args.max_count)
    
    if args.files_with_matches:
        # Group results by file_id
        results_by_file = defaultdict(int)
        for result in results:
            results_by_file[result['file_id']] += 1
        
        # Sort files by match count in descending order
        sorted_files = sorted(results_by_file.items(), key=lambda x: x[1], reverse=True)
        
        # Print file paths
        for file_id, count in sorted_files:
            full_path = db.file_by_id(file_id)['path']
            print(f"{relativize(full_path, args.path_to_code)}")
    else:
        for result in results:
            file_id = result['file_id']
            full_path = db.file_by_id(file_id)['path']
            print(f"# {relativize(full_path, args.path_to_code)} #")
            print(result['chunk'])
            print("\n" + "-" * 80 + "\n")  # Separator between chunks


def prune(args):
    # Create a dictionary mapping file paths to their document IDs
    file_docs = {}
    for doc in tqdm(db.hashes_cursor(), desc="Loading known files from Astra", bar_format='{desc}: {n_fmt}'):
        file_docs[doc['path']] = doc['_id']
    
    for file_path in args.files:
        full_path = os.path.abspath(file_path)
        if full_path in file_docs:
            db.delete(file_docs[full_path])
            print(f"Deleted {file_path} from the index.")
        else:
            print(f"File {file_path} not found in the index.")


def debug_chunks(args):
    full_path = os.path.abspath(os.path.join(args.path_to_code, args.file))
    file_doc = None
    for doc in db.hashes_cursor():
        if doc['path'] == full_path:
            file_doc = doc
            break
    
    if file_doc is None:
        print(f"File {args.file} not found in the index.")
        return

    file_id = file_doc['_id']
    print(f"File {args.file} present in the index with ID: {file_id}")
    chunks = db.get_chunks_by_file_id(file_id)
    
    if not chunks:
        print(f"No chunks found for file: {args.file}")
        return

    print(f"Chunks for file: {args.file}")
    for i, chunk in enumerate(chunks, 1):
        print(f"\nChunk {i}:")
        print(chunk['chunk'])


if __name__ == '__main__':
    args = parse_arguments()
    db.init(args.collection)
    if args.command == 'index':
        index(args)
    elif args.command == 'search':
        search(args)
    elif args.command == 'prune':
        prune(args)
    elif args.command == 'debug-chunks':
        debug_chunks(args)
    else:
        assert args.command == 'debug-index'
        debug_index(args)
