# ZenFS Architecture Reference

## 1. Overview

ZenFS is a custom filesystem hierarchy and volume management system for ZenOS. It provides a human-readable FHS using symlinks while maintaining compatibility with the standard NixOS structure. It also implements "Roaming Drives"—external storage devices that seamlessly merge into the main filesystem via a database-driven symlink system.

## 2. Directory Structure (Custom FHS)

All standard directories are hidden or abstracted.

| Directory | Target / Content                            | Description                                                 |
| :-------- | :------------------------------------------ | :---------------------------------------------------------- |
| `/System` | `/System/Packages`<br>`/System/Logs`        | System-level components.                                    |
| `/Live`   | `/Live/Temp`<br>`/Live/Devices`             | Volatile data. Contains `Drives/` (Nodes, UUID, Label, ID). |
| `/Config` | Symlinks to `/etc/*`                        | Categorized configurations.                                 |
| `/Apps`   | `/Apps/Binaries`                            | User-facing binaries and categorized `.desktop` files.      |
| `/Mount`  | `/Mount/Drives`<br>`/Mount/Roaming`         | Mount points.                                               |
| `/Users`  | `/Users/$USER`<br>`/Users/Admin` -> `/root` | User homes and Admin root.                                  |

### 2.1 Config Categories

The `/Config` directory is generated based on `/System/ZenFS/config_categories.json`.
**Categories:** `Audio`, `Bluetooth`, `Desktop`, `Display`, `Fonts`, `Hardware`, `Network`, `Nix`, `Security`, `Services`, `System`, `User`, `ZenOS`.
_Note: `/Config/ZenOS` is a user-writable folder for the system flake/config._

## 3. Drive & UUID Logic

### 3.1 Identifiers

- **ZenFS UUID**: 16 characters, alphanumeric (`[a-zA-Z0-9]`), case-sensitive.
- **Drive Config**: stored in `drive.json` at the drive root (`/System/ZenFS/drive.json`).

```json
{
  "uuid": "AbC123XyZ7890def",
  "label": "MyDrive",
  "type": "system", // or "roaming"
  "createdAt": 1706601600
}
```

### 3.2 Database ("Ghost Files")

Located at `/System/ZenFS/Database`. The content of the ghost file determines the origin.

| File Location | Ghost Content      | Meaning                                          |
| :------------ | :----------------- | :----------------------------------------------- |
| System Drive  | `.`                | File exists on the current (System) drive.       |
| Roaming Drive | `AbC123XyZ7890def` | File exists on the Roaming drive with this UUID. |

_Sync Logic_: When a Roaming Drive is connected, its DB entries (already containing its own UUID) are lazily copied into the System Drive's DB.

## 4. Automation & Scripts

- **Core Script** (`zenfs`): Handles mounting, config syncing, and DB merging.
- **Janitor Script** (`zenfs-janitor`): Handles broken link cleanup and empty directory pruning.
- **Notification**: The system notifies the user via `notify-send` when applying/syncing databases.
