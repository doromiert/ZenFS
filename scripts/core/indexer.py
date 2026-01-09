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
USERS_ROOT = "/Users" # Target for symlink projection

# System directories to ignore in the Root View
EXCLUDED_ROOTS = {
    'nix', 'proc', 'sys', 'dev', 'run', 'boot', 
    'etc', 'var', 'tmp', 'usr', 'bin', 'sbin', 
    'lib', 'lib64', 'mnt', 'media', 'srv', 'opt', 
    'System', 'Live', 'Mount', 'Users', 'Apps', 'Config'
}

# [ UPDATE ] Pseudo-directories to ignore in Music folders
MUSIC_PSEUDO_DIRS = {
    'Artists', 'Albums', 'Years', 'Genres', 'OSTs', '.building', '.trash_Artists', 
    '.trash_Albums', '.trash_Years', '.trash_Genres', '.trash_OSTs'
}

def get_drive_uuid(mount_point=None):
    path = ROOT_ID_FILE
    if mount_point:
        path = os.path.join(mount_point, "System/ZenFS/drive.json")
    
    if os.path.exists(path):
        try:
            with open(path, 'r') as f:
                data = json.load(f)
                return data['drive_identity']['uuid']
        except:
            pass
    return "UNKNOWN"

def get_conflict_name(filename, drive_uuid):
    p = Path(filename)
    return f"{p.stem}-{drive_uuid}{p.suffix}"

class ZenFSHandler(FileSystemEventHandler):
    def __init__(self, drive_root, drive_uuid, is_roaming=False):
        self.drive_root = drive_root
        self.drive_uuid = drive_uuid
        self.is_roaming = is_roaming
        
        # Determine Drive-Local DB path
        if is_roaming:
            self.local_db_root = os.path.join(drive_root, "System/ZenFS/Database")
        else:
            self.local_db_root = SYSTEM_DB # Root drive IS the system db

    def _get_rel_path(self, src_path):
        rel = os.path.relpath(src_path, self.drive_root)
        if rel == ".": rel = ""
        return rel

    def _is_ignored_path(self, path):
        """Checks if path is inside a Music Pseudo-Directory."""
        parts = Path(path).parts
        # Check if 'Music' is in path AND followed by a pseudo dir
        if 'Music' in parts:
            try:
                music_idx = parts.index('Music')
                if len(parts) > music_idx + 1:
                    subdir = parts[music_idx + 1]
                    if subdir in MUSIC_PSEUDO_DIRS:
                        return True
            except ValueError:
                pass
        return False

    def _ensure_dir_structure(self, base_path, rel_path):
        """Creates directory tree and writes folder identity."""
        target_dir = os.path.join(base_path, rel_path)
        if not os.path.exists(target_dir):
            try:
                os.makedirs(target_dir, exist_ok=True)
                os.chmod(target_dir, 0o755)
            except OSError:
                return target_dir

        # Write Metadata
        meta_file = os.path.join(target_dir, ".zenfs-folder-info")
        try:
            with open(meta_file, 'w') as f:
                f.write(self.drive_uuid)
            os.chmod(meta_file, 0o644)
        except Exception:
            pass
        return target_dir

    def _write_db_entry(self, db_root, rel_path, filename):
        """Writes the UUID pointer file to a specific database."""
        db_dir = os.path.join(db_root, rel_path)
        self._ensure_dir_structure(db_root, rel_path)
        
        target_path = os.path.join(db_dir, filename)
        
        # Conflict Handling (File collision in DB)
        if os.path.exists(target_path):
            try:
                with open(target_path, 'r') as f:
                    existing_uuid = f.read().strip()
                if existing_uuid != self.drive_uuid:
                    # Conflict: Use UUID suffix
                    target_path = os.path.join(db_dir, get_conflict_name(filename, self.drive_uuid))
            except:
                pass

        try:
            with open(target_path, 'w') as f:
                f.write(self.drive_uuid)
            os.chmod(target_path, 0o644)
        except Exception as e:
            print(f"DB Write Error ({target_path}): {e}")

    def _project_symlink(self, src_path, rel_path):
        """Creates a symlink in the Global /Users folder pointing to the Roaming file."""
        if not rel_path.startswith("Users/"):
            return

        target_sys_path = os.path.join("/", rel_path)
        
        # Check for collision
        final_target = target_sys_path
        if os.path.exists(target_sys_path) or os.path.islink(target_sys_path):
            # If it points to us already, skip
            if os.path.islink(target_sys_path) and os.readlink(target_sys_path) == src_path:
                return
            
            # Conflict: Projection must use conflict name
            parent = os.path.dirname(target_sys_path)
            name = os.path.basename(target_sys_path)
            final_target = os.path.join(parent, get_conflict_name(name, self.drive_uuid))

        # Create Symlink
        try:
            parent_dir = os.path.dirname(final_target)
            if not os.path.exists(parent_dir):
                os.makedirs(parent_dir, exist_ok=True)
                
            if not os.path.exists(final_target):
                os.symlink(src_path, final_target)
        except Exception as e:
            print(f"Projection Error: {e}")

    def _sync_file(self, src_path):
        if os.path.isdir(src_path): return
        if os.path.islink(src_path): return 
        if self._is_ignored_path(src_path): return # [ NEW ] Skip pseudo-files
        
        rel_path = os.path.dirname(self._get_rel_path(src_path))
        filename = os.path.basename(src_path)

        # 1. Update Drive-Local Database (Origin Drive)
        if self.is_roaming:
            self._write_db_entry(self.local_db_root, rel_path, filename)

        # 2. Update System Global Database (Root Drive)
        self._write_db_entry(SYSTEM_DB, rel_path, filename)

        # 3. Project Symlink (Hologram)
        if self.is_roaming:
            self._project_symlink(src_path, os.path.join(rel_path, filename))

    def _remove_file(self, src_path):
        if self._is_ignored_path(src_path): return

        rel_path = os.path.dirname(self._get_rel_path(src_path))
        filename = os.path.basename(src_path)
        
        names = [filename, get_conflict_name(filename, self.drive_uuid)]
        
        for n in names:
            db_file = os.path.join(SYSTEM_DB, rel_path, n)
            if os.path.exists(db_file):
                try:
                    with open(db_file, 'r') as f:
                        if f.read().strip() == self.drive_uuid:
                            os.remove(db_file)
                except: pass

        if self.is_roaming:
            for n in names:
                db_file = os.path.join(self.local_db_root, rel_path, n)
                if os.path.exists(db_file):
                    os.remove(db_file)

        if self.is_roaming and rel_path.startswith("Users/"):
            target_sys_path = os.path.join("/", rel_path, filename)
            targets = [target_sys_path, os.path.join(os.path.dirname(target_sys_path), get_conflict_name(filename, self.drive_uuid))]
            for t in targets:
                if os.path.islink(t) and os.readlink(t) == src_path:
                    os.remove(t)

    def on_created(self, event):
        if event.is_directory:
            pass
        else:
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

def initial_scan(root, uuid_str, is_roaming=False):
    print(f"Scanning {root} ({uuid_str})...")
    handler = ZenFSHandler(root, uuid_str, is_roaming)
    
    for dirpath, dirnames, filenames in os.walk(root):
        if root == '/':
            dirnames[:] = [d for d in dirnames if d not in EXCLUDED_ROOTS]
        
        # Skip ZenFS internals
        if "System/ZenFS" in dirpath:
            continue

        # [ NEW ] Skip Music Pseudo-dirs during walk
        if 'Music' in Path(dirpath).parts:
            # Modify dirnames in-place to prevent os.walk from entering them
            dirnames[:] = [d for d in dirnames if d not in MUSIC_PSEUDO_DIRS]

        for f in filenames:
            full_path = os.path.join(dirpath, f)
            handler._sync_file(full_path)

def main():
    print("::: ZenFS Librarian (Indexer) :::")
    
    if not os.path.exists(SYSTEM_DB):
        os.makedirs(SYSTEM_DB)
    os.chmod(SYSTEM_DB, 0o755)

    root_uuid = get_drive_uuid()
    observer = Observer()
    
    # 1. Watch Local Home
    if os.path.exists("/home"):
        initial_scan("/home", root_uuid, is_roaming=False)
        observer.schedule(ZenFSHandler("/", root_uuid, is_roaming=False), "/home", recursive=True)

    # 2. Watch Roaming Drives
    if os.path.exists(ROAMING_MOUNT_ROOT):
        for item in os.listdir(ROAMING_MOUNT_ROOT):
            mount_path = os.path.join(ROAMING_MOUNT_ROOT, item)
            if os.path.isdir(mount_path):
                r_uuid = get_drive_uuid(mount_path)
                initial_scan(mount_path, r_uuid, is_roaming=True)
                observer.schedule(ZenFSHandler(mount_path, r_uuid, is_roaming=True), mount_path, recursive=True)

    print("Librarian is watching.")
    observer.start()
    try:
        while True:
            time.sleep(5)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

if __name__ == "__main__":
    main()