######
# scripts/core/notify.py
######
import os
import subprocess
import pwd

def send(title, message, urgency="normal", icon="drive-harddisk"):
    """
    Sends a notification to the primary user session.
    Handles the context switch from Root (Systemd) to User (DBus).
    """
    try:
        # 1. Identify the primary user (Assumes UID 1000 for ZenOS single-user focus)
        # In a more complex setup, we'd iterate /run/user/* or check login sessions.
        target_uid = 1000
        try:
            user_record = pwd.getpwuid(target_uid)
            username = user_record.pw_name
        except KeyError:
            # Fallback if UID 1000 doesn't exist
            print(f"[Notify] UID {target_uid} not found. Skipping notification.")
            return

        # 2. Construct the DBus Address
        # NixOS typically places the user bus at /run/user/<uid>/bus
        dbus_address = f"unix:path=/run/user/{target_uid}/bus"
        
        if not os.path.exists(f"/run/user/{target_uid}/bus"):
            # User might not be logged in
            return

        # 3. Construct the command
        # We run as the user to respect permissions and ownership
        cmd = [
            "su", username, "-c",
            f"DBUS_SESSION_BUS_ADDRESS={dbus_address} notify-send -u {urgency} -i {icon} -a 'ZenOS' '{title}' '{message}'"
        ]

        # 4. Execute
        subprocess.run(cmd, check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    except Exception as e:
        print(f"[Notify] Error sending notification: {e}")