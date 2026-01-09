######
# scripts/user/mint.py
######
import os
import sys
import json
import uuid
import subprocess
import time

def check_root():
    if os.geteuid() != 0:
        print("Error: ZenFS Mint requires root privileges to access drives.")
        print("Please run with: sudo zenfs-mint")
        sys.exit(1)

def get_removable_drives():
    try:
        cmd = ["lsblk", "-J", "-o", "NAME,SIZE,MODEL,TRAN,MOUNTPOINT,FSTYPE"]
        result = subprocess.check_output(cmd)
        data = json.loads(result)
        
        candidates = []
        for dev in data.get("blockdevices", []):
            if dev.get("name", "").startswith("loop") or dev.get("name", "").startswith("zram"):
                continue
            candidates.append(dev)
        return candidates
    except Exception as e:
        print(f"Error scanning drives: {e}")
        return []

def mint_drive(device_node, label, mountpoint):
    """Initializes the ZenFS structure on the drive."""
    
    target_path = mountpoint
    temp_mount = False
    
    if not mountpoint:
        print(f"Drive {device_node} is not mounted. Mounting temporarily...")
        target_path = f"/tmp/zenfs_mint_{int(time.time())}"
        os.makedirs(target_path, exist_ok=True)
        try:
            subprocess.check_call(["mount", f"/dev/{device_node}", target_path])
            temp_mount = True
        except subprocess.CalledProcessError:
            print("Failed to mount drive. Is it formatted?")
            return False

    # [ UPDATE ] New ZenFS Structure
    system_dir = os.path.join(target_path, "System", "ZenFS")
    db_dir = os.path.join(system_dir, "Database")
    users_dir = os.path.join(target_path, "Users")
    identity_file = os.path.join(system_dir, "drive.json")
    
    # Check for existing identity
    if os.path.exists(identity_file):
        print(f"\n[!] WARNING: This drive already has a ZenFS identity!")
        override = input("Overwrite? (y/N): ").lower()
        if override != 'y':
            if temp_mount: subprocess.call(["umount", target_path])
            return False

    # Create Structure
    print("Creating directory hierarchy...")
    os.makedirs(db_dir, exist_ok=True)
    os.makedirs(users_dir, exist_ok=True)

    new_uuid = str(uuid.uuid4())
    data = {
        "drive_identity": {
            "uuid": new_uuid,
            "label": label,
            "type": "roaming",
            "created_at": time.time()
        }
    }
    
    try:
        with open(identity_file, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"\n[SUCCESS] Drive minted!")
        print(f"UUID:  {new_uuid}")
        print(f"Label: {label}")
        print(f"Path:  {identity_file}")
    except Exception as e:
        print(f"Error writing identity: {e}")
    finally:
        if temp_mount:
            subprocess.call(["umount", target_path])
            os.rmdir(target_path)
    
    return True

def main():
    print("::: ZenFS Drive Minter :::")
    check_root()
    
    drives = get_removable_drives()
    
    if not drives:
        print("No suitable drives found.")
        return

    print("\nAvailable Drives:")
    print(f"{'#':<3} {'DEVICE':<10} {'SIZE':<10} {'MODEL':<20} {'MOUNT':<15}")
    print("-" * 60)
    
    selection_map = {}
    idx = 1
    
    def print_dev(d, indent=0):
        nonlocal idx
        prefix = "  " * indent
        name = d.get('name')
        is_selectable = d.get('fstype') is not None
        
        sel_str = f"{idx}]" if is_selectable else "   "
        if is_selectable:
            selection_map[idx] = d
            idx += 1
            
        print(f"{sel_str:<3} {prefix}{name:<10} {d.get('size'):<10} {d.get('model', ''):<20} {str(d.get('mountpoint')):<15}")
        
        for child in d.get('children', []):
            print_dev(child, indent + 1)

    for d in drives:
        print_dev(d)

    print("-" * 60)
    
    try:
        choice = input("\nSelect drive number to mint (Ctrl+C to cancel): ")
        if not choice.isdigit(): return
        dev = selection_map.get(int(choice))
        if not dev: return
            
        label = input(f"Enter Label for {dev['name']}: ")
        if not label: label = "Unnamed_ZenFS_Drive"
            
        mint_drive(dev['name'], label, dev.get('mountpoint'))
        
    except KeyboardInterrupt:
        print("\nAborted.")

if __name__ == "__main__":
    main()