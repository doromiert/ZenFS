import os
import sys
import json
import shutil
import subprocess
import time

# [ IDENTITY ] The Janitor (Dumb Mode - Python Port)
# Spec: 2.0 (Executive Maintenance)

# --- Configuration Loading ---
config_env = os.environ.get("JANITOR_CONFIG")
if not config_env:
    print("[JANITOR-DUMB] Error: JANITOR_CONFIG env var not found.")
    sys.exit(1)

try:
    CONFIG = json.loads(config_env)
except json.JSONDecodeError as e:
    print(f"[JANITOR-DUMB] Error parsing config: {e}")
    sys.exit(1)

# Expand vars in watched_dirs
WATCHED_DIRS = [os.path.expandvars(d) for d in CONFIG.get("watched_dirs", ["$HOME/Downloads"])]
RAW_RULES = CONFIG.get("rules", {})
GRACE_PERIOD = CONFIG.get("grace_period", 60) # seconds

# Catch-all directory
RANDOM_DIR = os.path.join(os.path.expanduser("~"), "Random/Downloads")

# --- Precompute Suffix Rules ---
# We flatten the rules into a list of (suffix, destination) tuples
# and sort them by suffix length (descending).
# This ensures ".ps3.iso" is matched BEFORE ".iso".
SUFFIX_RULES = []
for folder, suffixes in RAW_RULES.items():
    dest_path = os.path.join(os.path.expanduser("~"), folder)
    for suffix in suffixes:
        # Normalize suffix: ensure it starts with '.' if strictly an extension, 
        # or leave as is if user provided dots.
        clean_suffix = suffix.lower()
        if not clean_suffix.startswith('.'):
            clean_suffix = '.' + clean_suffix
        SUFFIX_RULES.append((clean_suffix, dest_path))

# Sort by length descending (Longest Match First)
SUFFIX_RULES.sort(key=lambda x: len(x[0]), reverse=True)


def is_file_open(filepath):
    """
    Checks if a file is currently open by another process using lsof.
    """
    try:
        subprocess.check_call(["lsof", filepath], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except subprocess.CalledProcessError:
        return False
    except FileNotFoundError:
        return False

def is_grace_period_active(filepath):
    """
    Checks if file was modified recently (within GRACE_PERIOD).
    """
    try:
        mtime = os.path.getmtime(filepath)
        if time.time() - mtime < GRACE_PERIOD:
            return True
        return False
    except OSError:
        return False

def get_destination(filename):
    """
    Finds destination using Longest Suffix Match.
    """
    fname_lower = filename.lower()
    
    for suffix, dest_folder in SUFFIX_RULES:
        if fname_lower.endswith(suffix):
            return dest_folder
            
    return RANDOM_DIR

def process_directory(directory):
    if not os.path.exists(directory):
        print(f"[JANITOR-DUMB] Skipped (Not Found): {directory}")
        return

    print(f"[JANITOR-DUMB] Scanning {directory}...")
    
    with os.scandir(directory) as it:
        for entry in it:
            if not entry.is_file():
                continue
            
            # Skip hidden files
            if entry.name.startswith('.'):
                continue
                
            file_path = entry.path
            
            # 1. Check Grace Period
            if is_grace_period_active(file_path):
                # print(f" -> Waiting (Grace Period): {entry.name}")
                continue

            # 2. Check if busy (Open by app)
            if is_file_open(file_path):
                print(f" -> Busy: {entry.name}")
                continue

            # 3. Determine Destination
            dest_dir = get_destination(entry.name)

            # 4. Create Dest if needed
            if not os.path.exists(dest_dir):
                os.makedirs(dest_dir, exist_ok=True)

            # 5. Move with Rename Logic
            try:
                dest_path = os.path.join(dest_dir, entry.name)
                if os.path.exists(dest_path):
                    base, extension = os.path.splitext(entry.name)
                    counter = 1
                    while os.path.exists(os.path.join(dest_dir, f"{base}_{counter}{extension}")):
                        counter += 1
                    dest_path = os.path.join(dest_dir, f"{base}_{counter}{extension}")
                
                shutil.move(file_path, dest_path)
                print(f" -> Moved: {entry.name} to {dest_dir}")
                
            except Exception as e:
                print(f" -> Error moving {entry.name}: {e}")

def main():
    for d in WATCHED_DIRS:
        process_directory(d)

if __name__ == "__main__":
    main()