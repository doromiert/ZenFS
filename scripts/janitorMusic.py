import os
import sys
import json
import shutil
import re
import mutagen
from pathlib import Path

# [ IDENTITY ] The Janitor (Music View Generator)
# Spec: 6.2 (Symbolic Folders)

# --- Config ---
config_env = os.environ.get("JANITOR_MUSIC_CONFIG")
if not config_env:
    print("[JANITOR-MUSIC] Error: JANITOR_MUSIC_CONFIG env var not found.")
    sys.exit(1)

try:
    CONFIG = json.loads(config_env)
except json.JSONDecodeError as e:
    print(f"[JANITOR-MUSIC] Error parsing config: {e}")
    sys.exit(1)

MUSIC_DIR = Path(os.path.expandvars(CONFIG.get("musicDir", "$HOME/Music")))
SOURCE_DIR = Path(os.path.expandvars(CONFIG.get("unsortedDir", "$HOME/Music/.database")))
SPLITTERS = CONFIG.get("artistSplitSymbols", [";"])

# Regex to split artists
SPLIT_REGEX = f"[{''.join(map(re.escape, SPLITTERS))}]"

# Categories to generate
CATS = ["Artists", "Genres", "Years", "OSTs"]

def sanitize(name):
    """Sanitize directory names."""
    if not name: return "Unknown"
    name = str(name).strip()
    return re.sub(r'[<>:"/\\|?*]', '_', name)

def clear_views():
    """Removes existing generated views to ensure clean state."""
    for cat in CATS:
        target = MUSIC_DIR / cat
        if target.exists():
            if target.is_symlink():
                target.unlink()
            elif target.is_dir():
                shutil.rmtree(target)
            print(f"[JANITOR-MUSIC] Cleared view: {cat}")

def get_tags(filepath):
    """Extracts basic tags using Mutagen."""
    try:
        audio = mutagen.File(filepath, easy=True)
        if not audio: return None
        
        # Helper to get first item or None
        get = lambda k: audio.get(k, [None])[0]
        
        # Handle Artist Splitting
        raw_artist = get('artist') or "Unknown Artist"
        raw_album_artist = get('albumartist') or get('album artist')
        
        artists = [a.strip() for a in re.split(SPLIT_REGEX, raw_artist) if a.strip()]
        
        # Spec 6.2: "Artists Organized primarily by Album Artist"
        # If AlbumArtist exists, that's the main container, but we also want links for individual artists?
        # Implementing: "Multi-Visibility: Symlinks for collaborative tracks appear in folders for all involved artists."
        
        return {
            'artists': artists,
            'album_artist': raw_album_artist,
            'album': get('album') or "Unknown Album",
            'title': get('title') or filepath.stem,
            'year': get('date') or get('year') or "Unknown Year",
            'genre': get('genre') or "Unknown Genre"
        }
    except Exception as e:
        print(f"Error reading {filepath.name}: {e}")
        return None

def create_link(source_file, target_link):
    """Creates a symlink if it doesn't exist."""
    try:
        if not target_link.parent.exists():
            target_link.parent.mkdir(parents=True)
        
        if not target_link.exists():
            # Create absolute symlink
            os.symlink(source_file.resolve(), target_link)
    except Exception as e:
        print(f"Failed to link {target_link}: {e}")

def main():
    print(f"[JANITOR-MUSIC] Syncing views in {MUSIC_DIR} from {SOURCE_DIR}")
    
    if not SOURCE_DIR.exists():
        print(f"[JANITOR-MUSIC] Source {SOURCE_DIR} does not exist.")
        return

    # 1. Clear old views
    clear_views()

    # 2. Scan and Link
    count = 0
    for root, _, files in os.walk(SOURCE_DIR):
        for f in files:
            file_path = Path(root) / f
            
            # Skip non-audio (basic check)
            if f.startswith('.'): continue
            
            tags = get_tags(file_path)
            if not tags: continue

            # --- GENERATE VIEWS ---
            
            # A. ARTISTS VIEW
            # Structure: Artists/{Artist}/{Album}/{Title}.ext
            for artist in tags['artists']:
                s_artist = sanitize(artist)
                s_album = sanitize(tags['album'])
                
                link_path = MUSIC_DIR / "Artists" / s_artist / s_album / file_path.name
                create_link(file_path, link_path)

            # B. GENRES VIEW
            # Structure: Genres/{Genre}/{Artist} - {Title}.ext
            s_genre = sanitize(tags['genre'])
            link_path = MUSIC_DIR / "Genres" / s_genre / f"{tags['artists'][0]} - {tags['title']}{file_path.suffix}"
            create_link(file_path, link_path)

            # C. YEARS VIEW
            # Structure: Years/{Year}/{Album}/{Title}.ext
            # Extract year only (sometimes it's YYYY-MM-DD)
            year = str(tags['year'])[:4]
            s_year = sanitize(year)
            link_path = MUSIC_DIR / "Years" / s_year / sanitize(tags['album']) / file_path.name
            create_link(file_path, link_path)

            count += 1

    print(f"[JANITOR-MUSIC] Complete. Processed {count} tracks.")

if __name__ == "__main__":
    main()