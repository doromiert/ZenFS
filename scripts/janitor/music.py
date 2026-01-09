######
# scripts/janitor/music.py
######
import os
import sys
import json
import shutil
from pathlib import Path
import mutagen

# Import shared notify module
sys.path.append(os.path.join(os.path.dirname(__file__), '../core'))
import notify

# [ CONFIG ]
CONFIG_PATH = os.environ.get("JANITOR_CONFIG")

def load_config():
    if not CONFIG_PATH or not os.path.exists(CONFIG_PATH):
        raise FileNotFoundError("JANITOR_CONFIG not set")
    with open(CONFIG_PATH, 'r') as f:
        return json.load(f)['music']

def clear_symlinks(directory):
    """Recursively removes all symlinks in a directory."""
    if not directory.exists():
        return
    for item in directory.iterdir():
        if item.is_symlink():
            item.unlink()
        elif item.is_dir() and item.name != ".database":
            clear_symlinks(item)
            try:
                item.rmdir() # Remove empty dirs
            except OSError:
                pass

def create_symlink(source, dest):
    """Creates a symlink ensuring parent dirs exist."""
    try:
        if not dest.parent.exists():
            dest.parent.mkdir(parents=True, exist_ok=True)
        if not dest.exists():
            os.symlink(source, dest)
    except Exception as e:
        print(f"Link Error: {e}")

def sanitize_name(name):
    """Sanitizes strings for filesystem use."""
    if not name: return "Unknown"
    return "".join([c for c in name if c.isalnum() or c in " ._-"]).strip()

def generate_forest(config):
    db_root = Path(config['unsorted_dir'])
    view_root = Path(config['music_dir'])
    splitters = config.get('split_symbols', [';'])

    if not db_root.exists():
        print(f"Database root {db_root} does not exist.")
        return

    # 1. Clean existing views (EXCEPT .database)
    print("Clearing old views...")
    clear_symlinks(view_root)

    # 2. Iterate Database and Build Forest
    print("Regenerating Symlink Forest...")
    count = 0
    
    for item in db_root.rglob('*'):
        if item.is_file():
            try:
                # Use mutagen to read tags
                audio = mutagen.File(item, easy=True)
                if not audio:
                    continue
                
                # Extract Metadata (First item in list usually)
                artist = audio.get('artist', ['Unknown Artist'])[0]
                album = audio.get('album', ['Unknown Album'])[0]
                title = audio.get('title', [item.stem])[0]
                date = audio.get('date', ['0000'])[0][:4] # Year only
                genre = audio.get('genre', ['Unclassified'])[0]
                
                # Sanitize
                s_artist = sanitize_name(artist)
                s_album = sanitize_name(album)
                s_title = sanitize_name(title)
                s_year = sanitize_name(date)
                s_genre = sanitize_name(genre)

                filename = f"{s_title}{item.suffix}"

                # [ SPEC 6.2 ] Structure Generation
                
                # 1. Artists/[Artist]/[Album]/[Track]
                create_symlink(item, view_root / "Artists" / s_artist / s_album / filename)
                
                # 2. Years/[Year]/[Album]/[Track]
                create_symlink(item, view_root / "Years" / s_year / s_album / filename)
                
                # 3. Genres/[Genre]/[Track]
                create_symlink(item, view_root / "Genres" / s_genre / filename)
                
                # 4. OSTs (Heuristic: Genre contains 'Soundtrack' or Album contains 'OST')
                if 'Soundtrack' in genre or 'OST' in album:
                    create_symlink(item, view_root / "OSTs" / s_album / filename)

                count += 1
                
            except Exception as e:
                # Non-audio file or read error
                continue

    if count > 0:
        notify.send(
            "ZenOS Conductor",
            f"Forest Regenerated. Planted {count} tracks.",
            urgency="low",
            icon="audio-x-generic"
        )

def main():
    try:
        config = load_config()
        generate_forest(config)
    except Exception as e:
        print(f"Music Janitor Error: {e}")

if __name__ == "__main__":
    main()