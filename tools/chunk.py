import sys
import argparse
from pathlib import Path

# Add the project root directory to Python path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from ase.util import infer_language
from ase.chunking import chunkify_code

def main():
    parser = argparse.ArgumentParser(description="Chunk a single file.")
    parser.add_argument("file_path", help="Path to the file to be chunked")
    args = parser.parse_args()

    file_path = Path(args.file_path)
    
    if not file_path.is_file():
        print(f"Error: {file_path} is not a valid file.")
        sys.exit(1)

    with open(file_path, 'r') as file:
        code = file.read()
    
    language = infer_language(file_path)
    chunks = chunkify_code(code, language)
    
    print(f"File: {file_path} ({len(code)} characters in {language})")
    for i, chunk in enumerate(chunks):
        print(f"Chunk {i + 1}:")
        print(chunk)
        print('-' * 80)
    print()

if __name__ == "__main__":
    main()
