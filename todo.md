# ZenOS Implementation Plan

_Based on Spec 1.9 (Monitor & The Janitor)_

## 1. NixOS Modules (`modules/`)

### `modules/zenfs.nix` [ACTIVE]

- [ ] **Define Options**: `mainDrive`, `bootDrive`, `swapSize`.
- [ ] **System Integration**:
  - [ ] Create `systemd.services.zenfs-gatekeeper` (Mounting logic).
  - [ ] Create `systemd.services.zenfs-roaming` (Dynamic drive handling).
  - [ ] Define environment variables: `ZENFS_ROOT`, `ZENFS_GATE`.

### `modules/roaming.nix` [PENDING]

- [ ] **Define Options**: `enable`, `automount`, `mountPoint`.
- [ ] **Udev Integration**:
  - [ ] Create udev rule to trigger `scripts/core/roaming.py` on block device add/remove.

### `modules/janitor.nix`

- [ ] **Define Options**:
  - [ ] `dumb`: `enable`, `interval`, `gracePeriod`, `watchedDirs`, `rules`.
  - [ ] `music`: `enable`, `interval`, `musicDir`, `unsortedDir`.
- [ ] **System Integration**:
  - [ ] JSON Config Generation (Passes Nix config -> Python).
  - [ ] Create `systemd.services.zenfs-janitor-dumb` + Timer.
  - [ ] Create `systemd.services.zenfs-janitor-music` + Timer.

---

## 2. Core Scripts (`scripts/core/`)

### `mounting.py` (The Gatekeeper)

_Replaces legacy Bash activation script._

- [ ] **Gate Initialization**: Bind `/home` users to `/Users`.
- [ ] **XDG Enforcement**:
  - [ ] Auto-create directories (Projects, 3D, Android, etc.).
  - [ ] Apply permissions and ownership.
- [ ] **Shadow Database [Spec 4.1]**:
  - [ ] Initialize `/System/ZenFS/Database`.

### `roaming.py` (The Nomad) [PENDING]

_Implements Spec 4.2 & 5_

- [ ] **Detection**: Scan connected block devices for `.zenos.json`.
- [ ] **Mounting Strategy**: Mount to `/Mount/Roaming/[uuid]`.
- [ ] **Validation**: Enforce "The No-Nesting Rule".

---

## 3. Janitor Scripts (`scripts/janitor/`)

### `dumb.py` (The Sorting Deck)

_Implements Spec 2.1 & 2.2_

- [ ] **The Cluster Protocol**: Scan `watchedDirs`.
- [ ] **Sorting Logic**:
  - [ ] Read `rules` from JSON config.
  - [ ] Move files to target destinations.
  - [ ] Handle collisions (rename).
- [ ] **Safety**:
  - [ ] Respect `gracePeriod` (skip active downloads based on mtime).

### `music.py` (The Conductor)

_Implements Spec 6_

- [ ] **Symlink Forest**:
  - [ ] Clear old views (Artists, Albums, etc.).
  - [ ] Generate structure from `.database` (Basic implementation).
- [ ] **Swisstag Integration**:
  - [ ] Check for `swisstag` binary availability.
  - [ ] Run swisstag hook (if present).

### `ml.py` (The Oracle)

_Implements Spec 2.3 (Content Analysis & Ghosting)_

- [ ] **Service Structure**:
  - [ ] Define `JanitorML` class structure.
  - [ ] Implement config loader (intervals, model paths).
- [ ] **Inference Pipeline** (Stub/Basic):
  - [ ] **Image Analysis**: Detect "Screenshots" vs "Photos" (Resolution/Aspect Ratio heuristic first, ML model hook later).
  - [ ] **Text Analysis**: Detect "Code" vs "Prose" (Extension + Content heuristic).
- [ ] **The Suggestion Protocol (Ghost Logic)**:
  - [ ] Define JSON schema for Suggestions (`/System/ZenFS/Database/suggestions.json`).
  - [ ] Implement `suggest_move(file, target, confidence)` method.
  - [ ] **Janitor Prompt Integration**: Generate suggestions for files that `dumb.py` missed (e.g., "This PDF looks like an Invoice, move to Documents/Financial?").

---

## 4. Deferred (GUI/Monitor)

_Do not implement yet._

- [ ] **Dashboards**: Silicon Telemetry, The Gates (Visual).
- [ ] **Nix Pulse**: Service toggles.
- [ ] **Sync Center**: Syncthing GUI & `syncthing.nix` autogen.
- [ ] **Scheduled Hygiene**: Notifications.
