from argparse import Namespace
import os
import shutil
import sys
from pathlib import Path
import argparse

class FileCollector:
    source_dir: Path
    target_dir: Path
    extensions: set[str]
    moved_files: int
    skipped_files: int
    error_files: int
    total_files: int
    
    def __init__(self, source_dir: str, target_dir: str, extensions: list[str]):
        self.source_dir = Path(source_dir).resolve()
        self.target_dir = Path(target_dir).resolve()
        self.extensions = {ext.lower().lstrip('.') for ext in extensions}
        self.moved_files = 0
        self.skipped_files = 0
        self.error_files = 0
        self.total_files = 0
        
    def count_files(self) -> int:
        """Count total files to be processed for progress tracking"""
        count = 0
        try:
            for _, _, files in os.walk(self.source_dir):
                for file in files:
                    if self._has_target_extension(file):
                        count += 1
        except Exception as e:
            print(f"Error counting files: {e}")
        return count
    
    def _has_target_extension(self, filename: str) -> bool:
        """Check if file has one of the target extensions"""
        file_ext = Path(filename).suffix.lower().lstrip('.')
        return file_ext in self.extensions
    
    def _create_unique_filename(self, target_path: Path) -> Path:
        """Create a unique filename if the target already exists"""
        if not target_path.exists():
            return target_path
        
        base = target_path.stem
        suffix = target_path.suffix
        parent = target_path.parent
        counter = 1
        
        while True:
            new_name = f"{base}_{counter}{suffix}"
            new_path = parent / new_name
            if not new_path.exists():
                return new_path
            counter += 1
    
    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename to handle special characters"""
        # Characters that are problematic in Windows filenames
        invalid_chars = '<>:"/\\|?*'
        sanitized = filename
        
        for char in invalid_chars:
            sanitized = sanitized.replace(char, '_')
        
        # Remove leading/trailing spaces and dots
        sanitized = sanitized.strip(' .')
        
        # Ensure filename is not empty
        if not sanitized:
            sanitized = "unnamed_file"
            
        return sanitized
    
    def move_files(self, skip_existing: bool = True) -> None:
        """Main method to move files from source to target directory"""
        
        # Create target directory if it doesn't exist
        try:
            self.target_dir.mkdir(parents=True, exist_ok=True)
            print(f"Target directory: {self.target_dir}")
        except Exception as e:
            print(f"Error creating target directory: {e}")
            return
        
        # Count total files for progress tracking
        print("Counting files to process...")
        self.total_files = self.count_files()
        print(f"Found {self.total_files} files to process")
        
        if self.total_files == 0:
            print("No files found with the specified extensions.")
            return
        
        print(f"Starting file move process...")
        print(f"Source directory: {self.source_dir}")
        print(f"Target extensions: {', '.join(sorted(self.extensions))}")
        print("-" * 60)
        
        processed = 0
        
        try:
            for root, _, files in os.walk(self.source_dir):
                root_path = Path(root)
                
                for file in files:
                    if not self._has_target_extension(file):
                        continue
                    
                    processed += 1
                    source_file = root_path / file
                    
                    # Sanitize filename
                    sanitized_name = self._sanitize_filename(file)
                    target_file = self.target_dir / sanitized_name
                    
                    # Show progress
                    progress = (processed / self.total_files) * 100
                    print(f"[{progress:.1f}%] Processing: {file}")
                    
                    try:
                        if target_file.exists() and skip_existing:
                            print(f"  → Skipped (already exists): {sanitized_name}")
                            self.skipped_files += 1
                        else:
                            # If not skipping existing files, create unique name
                            if target_file.exists() and not skip_existing:
                                target_file = self._create_unique_filename(target_file)
                                print(f"  → Renamed to: {target_file.name}")
                            
                            # Move the file (with enhanced error handling)
                            try:
                                shutil.move(str(source_file), str(target_file))
                                print(f"  → Moved to: {target_file.name}")
                                self.moved_files += 1
                            except PermissionError:
                                print(f"  → Error: Permission denied for {file}")
                                self.error_files += 1
                            except OSError as e:
                                if "being used by another process" in str(e):
                                    print(f"  → Error: File {file} is in use by another process")
                                else:
                                    print(f"  → Error: OS error moving {file}: {e}")
                                self.error_files += 1
                            except Exception as e:
                                print(f"  → Error: Unexpected error moving {file}: {e}")
                                self.error_files += 1
                            
                    except Exception as e:
                        print(f"  → Error processing {file}: {e}")
                        self.error_files += 1
                        continue
        
        except KeyboardInterrupt:
            print("\nOperation cancelled by user.")
        except Exception as e:
            print(f"Error during file processing: {e}")
        
        # Print summary
        print("-" * 60)
        print("Move operation completed!")
        print(f"Total files processed: {processed}")
        print(f"Files moved: {self.moved_files}")
        print(f"Files skipped: {self.skipped_files}")
        print(f"Files with errors: {self.error_files}")
        print(f"Target directory: {self.target_dir}")

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Recursively search and move files with specific extensions",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
            Examples:
            python file_collector.py /source/path /target/path
            python file_collector.py C:\\Documents D:\\Backup --no-skip
            python file_collector.py /home/user/docs /backup --extensions pdf docx txt
        """
    )

    _ = parser.add_argument('source', type=str, help='Source directory to search')
    _ = parser.add_argument('target', type=str, help='Target directory to move files to')
    _ = parser.add_argument(
        '--extensions', 
        nargs='+', 
        default=['pdf', 'docx', 'zip', 'xlsm', 'pptx', 'txt', 'jpg', 'jpeg', 'mp4'],
        help='File extensions to search for (default: pdf docx zip xlsm pptx txt jpg jpeg mp4)'
    )
    _ = parser.add_argument(
        '--no-skip', 
        action='store_true',
        help='Do not skip existing files (create unique names instead)'
    )

    args: Namespace = parser.parse_args()
    
    # Validate source directory - cast to str to resolve type annotation warning
    source_str: str = args.source
    source_path = Path(source_str)
    if not source_path.exists():
        print(f"Error: Source directory '{source_str}' does not exist.")
        sys.exit(1)
    
    if not source_path.is_dir():
        print(f"Error: '{args.source}' is not a directory.")
        sys.exit(1)
    
    # Create file collector instance
    collector = FileCollector(str(args.source), str(args.target), args.extensions)
    
    # Start moving files
    skip_existing = not args.no_skip
    collector.move_files(skip_existing=skip_existing)

if __name__ == "__main__":
    main()