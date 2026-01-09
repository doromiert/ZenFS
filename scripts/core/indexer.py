######
# scripts/core/indexer.py
######
import os
import sys
import time
import json
import shutil
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# [ CONSTANTS ]
SYSTEM_DB = "/System/ZenFS/Database"
ROOT_ID_FILE = "/System/ZenFS/drive.json"
ROAMING_MOUNT_ROOT = "/Mount/Roaming"

# System directories to ignore in the Root View
EXCLUDED_ROOTS = {
    'nix', 'proc', 'sys', 'dev', 'run', 'boot', 
    'etc', 'var', 'tmp', 'usr', 'bin', 'sbin', 
    'lib', 'lib64', 'mnt', 'media', 'srv', 'opt', 
    'System', 'Live', 'Mount', 'Users', 'Apps', 'Config'
}

def get_drive_uuid(mount_point=None):
    """Gets UUID. If mount_point is None, assumes Root."""
    path = ROOT_ID_FILE
    if mount_point:
        path = os.path.join(mount_point, ".zenos.json")
    
    if os.path.exists(path):
        try:
            with open(path, 'r') as f:
                data = json.load(f)
                return data['drive_identity']['uuid']
        except:
            pass
    return "UNKNOWN"

def get_conflict_name(filename, drive_uuid):
    """Generates: filename-UUID.ext"""
    p = Path(filename)
    return f"{p.stem}-{drive_uuid}{p.suffix}"

class ZenFSHandler(FileSystemEventHandler):
    def __init__(self, drive_root, drive_uuid):
        self.drive_root = drive_root
        self.drive_uuid = drive_uuid
        self.is_roaming = (drive_root != '/')

    def _get_db_path(self, src_path):
        """Maps a physical path to the Union Database path."""
        rel = os.path.relpath(src_path, self.drive_root)
        if rel == ".": rel = ""
        return os.path.join(SYSTEM_DB, rel)

    def _sync_file(self, src_path):
        """Creates/Updates the text pointer in DB."""
        if os.path.isdir(src_path): return # Handled by dir logic
        
        db_path = self._get_db_path(src_path)
        db_dir = os.path.dirname(db_path)
        
        if not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
            
        # [ CONFLICT LOGIC ]
        final_path = db_path
        if os.path.exists(db_path):
            # Check if it's the same file (same UUID)
            try:
                with open(db_path, 'r') as f:
                    existing_uuid = f.read().strip()
                
                if existing_uuid != self.drive_uuid:
                    # Conflict! Use conflict naming
                    filename = os.path.basename(db_path)
                    conflict_name = get_conflict_name(filename, self.drive_uuid)
                    final_path = os.path.join(db_dir, conflict_name)
                    # Note: We don't overwrite the existing "Primary" link
            except:
                pass # Unreadable or empty? Overwrite safely.

        # Write UUID Struct
        try:
            with open(final_path, 'w') as f:
                f.write(self.drive_uuid)
        except Exception as e:
            print(f"Error syncing {src_path}: {e}")

    def _remove_file(self, src_path):
        """Removes the pointer from DB."""
        db_path = self._get_db_path(src_path)
        
        # Check primary
        if os.path.exists(db_path):
            try:
                with open(db_path, 'r') as f:
                    uuid = f.read().strip()
                if uuid == self.drive_uuid:
                    os.remove(db_path)
                    return
            except: pass
            
        # Check if it exists as a conflict file
        filename = os.path.basename(db_path)
        conflict_name = get_conflict_name(filename, self.drive_uuid)
        conflict_path = os.path.join(os.path.dirname(db_path), conflict_name)
        
        if os.path.exists(conflict_path):
            os.remove(conflict_path)

    def on_created(self, event):
        if not event.is_directory:
            self._sync_file(event.src_path)

    def on_modified(self, event):
        if not event.is_directory:
            self._sync_file(event.src_path)

    def on_moved(self, event):
        if not event.is_directory:
            self._remove_file(event.src_path)
            self._sync_file(event.dest_path)

    def on_deleted(self, event):
        if not event.is_directory:
            self._remove_file(event.src_path)

def initial_scan(root, uuid_str):
    """Performs a one-time scan on startup."""
    print(f"Scanning {root} ({uuid_str})...")
    handler = ZenFSHandler(root, uuid_str)
    
    for dirpath, dirnames, filenames in os.walk(root):
        # Exclusion for Root Drive
        if root == '/':
            dirnames[:] = [d for d in dirnames if d not in EXCLUDED_ROOTS]
        
        for f in filenames:
            full_path = os.path.join(dirpath, f)
            handler._sync_file(full_path)

def main():
    print("::: ZenFS Librarian (Indexer) :::")
    
    # 1. Setup Root Watcher
    root_uuid = get_drive_uuid()
    observer = Observer()
    
    # We can't watch '/' recursively on Linux easily without hitting /proc.
    # Strategy: Watch /home and specific user dirs.
    # For now, we assume user data is in /home.
    if os.path.exists("/home"):
        initial_scan("/home", root_uuid)
        observer.schedule(ZenFSHandler("/", root_uuid), "/home", recursive=True)

    # 2. Setup Roaming Watchers
    # Scan currently mounted drives
    if os.path.exists(ROAMING_MOUNT_ROOT):
        for item in os.listdir(ROAMING_MOUNT_ROOT):
            mount_path = os.path.join(ROAMING_MOUNT_ROOT, item)
            if os.path.isdir(mount_path):
                r_uuid = get_drive_uuid(mount_path)
                # Map Roaming Content -> Union DB
                initial_scan(mount_path, r_uuid)
                observer.schedule(ZenFSHandler(mount_path, r_uuid), mount_path, recursive=True)

    print("Librarian is watching.")
    observer.start()
    try:
        while True:
            time.sleep(5)
            # Todo: Dynamic watcher addition for new drives (handled by restart trigger in Roaming.py?)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

if __name__ == "__main__":
    main()