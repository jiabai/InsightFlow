import os
import time

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
UPLOAD_DIR = os.path.join(BASE_DIR, 'upload_file')
COMPLETED_DIR = os.path.join(BASE_DIR, 'completed')

# print(BASE_DIR)
# print(UPLOAD_DIR)
# print(COMPLETED_DIR)

def is_entries_valid(entries_list):
    if not any(True for _ in entries_list):
        time.sleep(5)
        return False
    return True

files_to_process = None
with os.scandir(UPLOAD_DIR) as entries:
    # Convert entries to list to allow multiple iterations
    entries_list = list(entries)
    # Print entries content before validation
    print("Entries content:", [entry.name for entry in entries_list])
    if not is_entries_valid(entries_list):
        pass  # entries will be closed automatically by context manager
    else:
        for entry in entries_list:
            print(entry.name)
            if entry.is_dir():
                user_id = entry.name
                user_path = os.path.join(UPLOAD_DIR, user_id)
                # Process files in user directory
                for file in os.listdir(user_path):
                    if file.endswith('.md'):
                        file_path = os.path.join(user_path, file)
                        if os.path.isfile(file_path):
                            # Store tuple of (file_path, file_name, user_id)
                            files_to_process = file_path

print(files_to_process)
