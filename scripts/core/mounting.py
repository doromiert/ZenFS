######
# scripts/core/mounting.py
######
import os
import sys
import subprocess
import pwd
import grp
import stat

# [ CONSTANTS ]
USERS_ROOT = "/Users"
SYSTEM_DB = "/System/ZenFS/Database"
XDG_TEMPLATE = [
    "Projects", "3D", "Android", "AI", "Apps & Scripts", 
    "Doom", "Rift", "Misc", "Passwords", "Downloads/Waiting"
]

def run_command(cmd):
    """Executes a shell command silently."""
    try:
        subprocess.run(cmd, check=True, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError:
        pass

def ensure_dir(path, uid, gid, mode=0o755):
    """Creates a directory with specific permissions if it doesn't exist."""
    if not os.path.exists(path):
        os.makedirs(path)
    os.chmod(path, mode)
    os.chown(path, uid, gid)

def is_mounted(path):
    """Checks if a path is a mount point."""
    return os.path.ismount(path)

def bind_user_gate(username, home_dir):
    """Binds a user's home to the ZenFS /Users gate."""
    target = os.path.join(USERS_ROOT, username)
    
    if not os.path.exists(target):
        os.makedirs(target)
    
    if not is_mounted(target):
        print(f"[Gatekeeper] Binding {username} -> {target}")
        run_command(f"mount --bind '{home_dir}' '{target}'")
    
    # [ CUSTOM ] Autogen XDG Directories
    try:
        user_info = pwd.getpwnam(username)
        uid, gid = user_info.pw_uid, user_info.pw_gid
        
        for folder in XDG_TEMPLATE:
            full_path = os.path.join(home_dir, folder)
            ensure_dir(full_path, uid, gid)
            
        # [ SPEC 6.1 ] Music Source of Truth
        music_db = os.path.join(home_dir, "Music", ".database")
        ensure_dir(music_db, uid, gid, 0o700)
        
    except KeyError:
        print(f"[Gatekeeper] Error: User {username} not found in passwd database.")

def init_shadow_db():
    """Initializes the system-wide shadow database directory."""
    if not os.path.exists(SYSTEM_DB):
        os.makedirs(SYSTEM_DB)
    os.chmod(SYSTEM_DB, 0o700)

def main():
    print("ZenFS Gatekeeper: Initializing...")
    
    # 1. Initialize System Gates
    init_shadow_db()
    
    # 2. Iterate /home users and bind
    if os.path.exists("/home"):
        for item in os.listdir("/home"):
            full_path = os.path.join("/home", item)
            if os.path.isdir(full_path):
                bind_user_gate(item, full_path)
    
    # 3. Bind Admin (Root)
    bind_user_gate("Admin", "/root")

    print("ZenFS Gatekeeper: Gates are open.")

if __name__ == "__main__":
    main()