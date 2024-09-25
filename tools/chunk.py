from util import get_indexable_files, infer_language
from chunking import chunkify_code

def main():
    root_dir = "."  # You can change this to the desired root directory
    indexable_files = get_indexable_files(root_dir)
    
    for file_path in indexable_files:
        with open(file_path, 'r') as file:
            code = file.read()
        
        language = infer_language(file_path)
        chunks = chunkify_code(code, language)
        
        print(f"File: {file_path}")
        for i, chunk in enumerate(chunks):
            print(f"  Chunk {i + 1}:")
            print(f"    {chunk[:100]}...")  # Display first 100 characters of the chunk
        print()

if __name__ == "__main__":
    main()
