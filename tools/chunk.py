import sys
from pathlib import Path

# Add the project root directory to Python path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from ase.util import get_indexable_files, infer_language
from ase.chunking import chunkify_code

def main():
    root_dir = "."  # You can change this to the desired root directory
    indexable_files = get_indexable_files(root_dir)
    
    for file_path in indexable_files:
        with open(file_path, 'r') as file:
            code = file.read()
        
        language = infer_language(file_path)
        chunks = chunkify_code(code, language)
        
        print(f"File: {file_path} ({len(code)} in {language})")
        for i, chunk in enumerate(chunks):
            print(f"  Chunk {i + 1}:")
            print(f"    {chunk[:100]}...")  # Display first 100 characters of the chunk
        print()

if __name__ == "__main__":
    main()
