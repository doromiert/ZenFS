######
# scripts/core/roaming.py
######
import os
import json
import subprocess
import time
import shutil
from pathlib import Path

import notify

# [ CONSTANTS ]
LIVE_ROOT = "/Live/Drives"
ROAMING_ROOT = os.environ.get("ZENFS_ROAMING_ROOT", "/Mount/Roaming")

def run_command(cmd):
    try:
        subprocess.run(cmd, check=True, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except subprocess.CalledProcessError:
        return False

def get_block_devices():
    """Returns a list of block devices with UUIDs using lsblk."""
    try:
        output = subprocess.check_output(
            ["lsblk", "-J", "-o", "NAME,UUID,LABEL,FSTYPE,MOUNTPOINT"],
            text=True
        )
        data = json.loads(output)
        devices = []
        for device in data.get("blockdevices", []):
            def extract(node):
                if node.get("uuid") and node.get("fstype"):
                    devices.append(node)
                for child in node.get("children", []):
                    extract(child)
            extract(device)
        return devices
    except Exception as e:
        print(f"[Nomad] Error scanning devices: {e}")
        return []

def is_mounted(path):
    return os.path.ismount(path)

def read_identity(mount_path):
    """Checks for .zenos.json and returns the UUID if valid."""
    identity_file = os.path.join(mount_path, ".zenos.json")
    if os.path.exists(identity_file):
        try:
            with open(identity_file, 'r') as f:
                data = json.load(f)
                return data.get("drive_identity", {}).get("uuid")
        except:
            pass
    return None

def reconcile():
    print("[Nomad] Starting reconciliation...")
    
    current_devices = get_block_devices()
    device_uuids = {d['uuid']: d for d in current_devices}
    
    # 1. MOUNT PHYSICAL DRIVES TO /Live/Drives
    for uuid, dev in device_uuids.items():
        live_path = os.path.join(LIVE_ROOT, uuid)
        dev_path = f"/dev/{dev['name']}"
        
        if not dev.get("mountpoint"):
            if not os.path.exists(live_path):
                os.makedirs(live_path)
            
            if not is_mounted(live_path):
                print(f"[Nomad] Mounting physical: {dev_path} -> {live_path}")
                run_command(f"mount {dev_path} {live_path}")

    # 2. MANAGE ROAMING GATES
    if os.path.exists(LIVE_ROOT):
        for item in os.listdir(LIVE_ROOT):
            live_path = os.path.join(LIVE_ROOT, item)
            if not is_mounted(live_path):
                try: os.rmdir(live_path)
                except: pass
                continue

            zen_id = read_identity(live_path)
            
            if zen_id:
                roaming_gate = os.path.join(ROAMING_ROOT, zen_id)
                
                if not os.path.exists(roaming_gate):
                    os.makedirs(roaming_gate)
                
                if not is_mounted(roaming_gate):
                    print(f"[Nomad] Identity found ({zen_id}). Opening Gate.")
                    run_command(f"mount --bind {live_path} {roaming_gate}")
                    
                    # [ NOTIFY ]
                    notify.send(
                        "ZenOS Nomad", 
                        f"Roaming Drive Connected: {zen_id}", 
                        icon="drive-removable-media"
                    )
            
    # 3. CLEANUP STALE GATES
    if os.path.exists(ROAMING_ROOT):
        for item in os.listdir(ROAMING_ROOT):
            gate_path = os.path.join(ROAMING_ROOT, item)
            
            # Simple check: If the bind source is gone, we might be stale.
            # But with lazy unmounting, it's hard to tell without checking /proc/mounts
            # For now, we trust the system.
            pass

if __name__ == "__main__":
    reconcile()