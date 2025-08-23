#!/usr/bin/env python3
"""
Example usage of the FileCollector class - Updated for moving files
"""

from file_collector import FileCollector
from pathlib import Path
import os

def example_basic_usage():
    """Basic usage example"""
    print("=== Basic Usage Example ===")
    
    # Define source and target directories
    source_dir = input("Enter source directory path: ").strip()
    target_dir = input("Enter target directory path: ").strip()
    
    # Default extensions
    extensions = ['pdf', 'docx', 'zip', 'xlsm', 'pptx', 'txt', 'jpg', 'jpeg', 'mp4']
    
    # Create collector instance
    collector = FileCollector(source_dir, target_dir, extensions)
    
    # Start moving (skip existing files by default)
    collector.move_files(skip_existing=True)

def example_custom_extensions():
    """Example with custom file extensions"""
    print("=== Custom Extensions Example ===")
    
    source_dir = input("Enter source directory path: ").strip()
    target_dir = input("Enter target directory path: ").strip()
    
    # Custom extensions - only image files
    extensions = ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'tiff']
    
    collector = FileCollector(source_dir, target_dir, extensions)
    collector.move_files(skip_existing=True)

def example_no_skip():
    """Example that doesn't skip existing files"""
    print("=== No Skip Example ===")
    
    source_dir = input("Enter source directory path: ").strip()
    target_dir = input("Enter target directory path: ").strip()
    
    extensions = ['pdf', 'docx', 'txt']
    
    collector = FileCollector(source_dir, target_dir, extensions)
    # Don't skip existing files - create unique names instead
    collector.move_files(skip_existing=False)

def migrate_wechat_files():
    """Migrate all files from WeChat Files directory to Temp directory"""
    print("=== WeChat Files Migration ===")
    
    # Define source and target directories
    source_dir = r"D:\WeChat Files"
    target_dir = r"D:\Temp"
    
    # Check if source directory exists
    if not os.path.exists(source_dir):
        print(f"Error: WeChat Files directory '{source_dir}' does not exist.")
        print("Please check if the path is correct or if WeChat is installed.")
        return
    
    # Get all file extensions (migrate all files, not just specific types)
    print("Scanning for all file types in WeChat Files directory...")
    all_extensions = set()
    
    try:
        for root, dirs, files in os.walk(source_dir):
            for file in files:
                ext = Path(file).suffix.lower().lstrip('.')
                if ext:  # Only add non-empty extensions
                    all_extensions.add(ext)
    except Exception as e:
        print(f"Error scanning directory: {e}")
        return
    
    if not all_extensions:
        print("No files found in the WeChat Files directory.")
        return
    
    print(f"Found files with extensions: {', '.join(sorted(all_extensions))}")
    
    # Confirm before proceeding
    response = input(f"\nThis will MOVE all files from:\n  {source_dir}\nto:\n  {target_dir}\n\nSource files will be removed after moving. Continue? (y/N): ")
    
    if response.lower() not in ['y', 'yes']:
        print("Operation cancelled.")
        return
    
    # Create collector instance with all found extensions
    collector = FileCollector(source_dir, target_dir, list(all_extensions))
    
    print(f"\nStarting migration of WeChat files...")
    print(f"Source: {source_dir}")
    print(f"Target: {target_dir}")
    print("=" * 60)
    
    try:
        # Start moving files (don't skip existing - create unique names)
        collector.move_files(skip_existing=False)
        
        print("\n" + "=" * 60)
        print("WeChat Files Migration Summary:")
        print(f"Files successfully moved: {collector.moved_files}")
        print(f"Files skipped: {collector.skipped_files}")
        print(f"Files with errors: {collector.error_files}")
        
        if collector.error_files > 0:
            print(f"\nNote: {collector.error_files} files could not be moved due to errors.")
            print("Common causes: files in use, permission issues, or system files.")
        
        if collector.moved_files > 0:
            print(f"\nFiles have been moved to: {target_dir}")
            print("Please verify the migration was successful before deleting any remaining files.")
        
    except KeyboardInterrupt:
        print("\nMigration interrupted by user.")
        print("Some files may have been moved. Please check both directories.")
    except Exception as e:
        print(f"\nUnexpected error during migration: {e}")

def example_safe_migration():
    """Example of safe migration with confirmation and error handling"""
    print("=== Safe Migration Example ===")
    
    source_dir = input("Enter source directory path: ").strip()
    target_dir = input("Enter target directory path: ").strip()
    
    # Validate directories
    if not os.path.exists(source_dir):
        print(f"Error: Source directory '{source_dir}' does not exist.")
        return
    
    if not os.path.isdir(source_dir):
        print(f"Error: '{source_dir}' is not a directory.")
        return
    
    # Show what will be moved
    extensions = ['pdf', 'docx', 'zip', 'xlsm', 'pptx', 'txt', 'jpg', 'jpeg', 'mp4']
    collector = FileCollector(source_dir, target_dir, extensions)
    
    # Count files first
    file_count = collector.count_files()
    print(f"\nFound {file_count} files to move with extensions: {', '.join(extensions)}")
    
    if file_count == 0:
        print("No files found to move.")
        return
    
    # Confirm operation
    response = input(f"\nThis will MOVE {file_count} files from '{source_dir}' to '{target_dir}'.\nSource files will be removed. Continue? (y/N): ")
    
    if response.lower() not in ['y', 'yes']:
        print("Operation cancelled.")
        return
    
    # Perform the move
    collector.move_files(skip_existing=False)

if __name__ == "__main__":
    print("File Collector Examples - Move Operations")
    print("1. Basic usage (default extensions)")
    print("2. Custom extensions (images only)")
    print("3. No skip mode (create unique names)")
    print("4. Migrate WeChat Files to Temp directory")
    print("5. Safe migration with confirmation")
    
    choice = input("\nSelect example (1-5): ").strip()
    
    if choice == "1":
        example_basic_usage()
    elif choice == "2":
        example_custom_extensions()
    elif choice == "3":
        example_no_skip()
    elif choice == "4":
        migrate_wechat_files()
    elif choice == "5":
        example_safe_migration()
    else:
        print("Invalid choice. Running WeChat migration...")
        migrate_wechat_files()