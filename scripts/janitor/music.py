######
# scripts/janitor/music.py
######
import os
import sys
import json
import shutil
import re
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

def create_symlink(source, dest):
    """Creates a symlink ensuring parent dirs exist."""
    try:
        if not dest.parent.exists():
            dest.parent.mkdir(parents=True, exist_ok=True)
        # Force overwrite if exists (shouldn't happen in clean temp build, but safe)
        if dest.exists() or dest.is_symlink():
            dest.unlink()
        os.symlink(source, dest)
    except Exception as e:
        # Silently fail on individual link errors to keep forest growing
        pass

def sanitize_name(name):
    """
    Sanitizes strings for filesystem use.
    Updated to be PERMISSIVE: preserves $, &, spaces, etc.
    Only removes characters that strictly break the filesystem.
    """
    if not name: return "Unknown"
    
    # 1. Replace path separators
    name = name.replace("/", "-").replace("\\", "-")
    
    # 2. Remove null bytes and non-printables
    name = "".join(c for c in name if c.isprintable())
    
    # 3. Trim reserved filenames (like "." or "..") and whitespace
    name = name.strip()
    if name in [".", ".."]: return "Unknown"
    
    return name if name else "Unknown"

def get_list(audio, key):
    """Helper to safely get a list of values from mutagen tags."""
    val = audio.get(key)
    if not val:
        return []
    if isinstance(val, list):
        return val
    return [str(val)]

def generate_forest(config):
    db_root = Path(config['unsorted_dir'])
    view_root = Path(config['music_dir'])
    split_symbols = config.get('split_symbols', [';', ','])
    
    # [ HOTSWAP ] Build in a hidden temporary directory first
    build_root = view_root / ".building"
    if build_root.exists():
        shutil.rmtree(build_root)
    build_root.mkdir()

    if not db_root.exists():
        print(f"Database root {db_root} does not exist.")
        return

    print("Regenerating Symlink Forest (Hotswap Mode)...")
    count = 0
    
    # Pre-compile split regex
    # Escapes symbols for regex (e.g., "." -> "\.")
    split_pattern = '|'.join(map(re.escape, split_symbols))

    for item in db_root.rglob('*'):
        if item.is_file():
            try:
                # Use mutagen to read tags
                audio = mutagen.File(item, easy=True)
                if not audio:
                    continue
                
                # Extract Metadata
                # Mutagen EasyID3 returns lists. We handle them properly now.
                artists_raw = get_list(audio, 'artist')
                album_artists_raw = get_list(audio, 'albumartist') # fallback
                albums_raw = get_list(audio, 'album')
                titles_raw = get_list(audio, 'title')
                dates_raw = get_list(audio, 'date')
                genres_raw = get_list(audio, 'genre')
                
                # Basic normalization
                title = titles_raw[0] if titles_raw else item.stem
                album = albums_raw[0] if albums_raw else "Unknown Album"
                # Use Year only (first 4 chars)
                year = dates_raw[0][:4] if dates_raw else "0000"
                
                # [ LOGIC ] Artist Splitting
                # Process the artist list and split strings containing separators
                final_artists = set()
                
                # Combine artist + albumartist for visibility
                source_artists = artists_raw if artists_raw else (album_artists_raw if album_artists_raw else ["Unknown Artist"])

                for entry in source_artists:
                    # Split by config symbols (e.g. "bbno$; Yung Gravy")
                    if split_pattern:
                        parts = re.split(split_pattern, entry)
                    else:
                        parts = [entry]
                    
                    for part in parts:
                        cleaned = part.strip()
                        if cleaned:
                            final_artists.add(cleaned)

                s_title = sanitize_name(title)
                s_album = sanitize_name(album)
                s_year = sanitize_name(year)
                
                filename = f"{s_title}{item.suffix}"

                # [ STRUCTURE GENERATION ]
                # All created in build_root

                # 1. Artists/[Artist]/[Album]/[Track]
                for artist in final_artists:
                    s_artist = sanitize_name(artist)
                    create_symlink(item, build_root / "Artists" / s_artist / s_album / filename)
                
                # 2. Years/[Year]/[Album]/[Track]
                create_symlink(item, build_root / "Years" / s_year / s_album / filename)
                
                # 3. Genres/[Genre]/[Track]
                for genre in genres_raw:
                    s_genre = sanitize_name(genre)
                    create_symlink(item, build_root / "Genres" / s_genre / filename)
                
                # 4. OSTs
                # Check all genres/albums for soundtrack keywords
                is_ost = any('soundtrack' in g.lower() for g in genres_raw) or 'ost' in album.lower()
                if is_ost:
                    create_symlink(item, build_root / "OSTs" / s_album / filename)

                count += 1
                
            except Exception as e:
                # print(f"Skipping {item.name}: {e}")
                continue

    # [ HOTSWAP EXECUTION ]
    # Atomic swap of the generated folders
    categories = ["Artists", "Years", "Genres", "OSTs"]
    
    for cat in categories:
        new_dir = build_root / cat
        target_dir = view_root / cat
        trash_dir = view_root / f".trash_{cat}"
        
        # Only swap if we actually generated something for this category
        # OR if we want to clear empty categories. Assuming we want complete sync.
        
        if new_dir.exists():
            # 1. Move old active to trash (Atomic rename)
            if target_dir.exists():
                try:
                    target_dir.rename(trash_dir)
                except OSError as e:
                    print(f"Hotswap Fail (Trash): {e}")
                    continue
            
            # 2. Move new build to active (Atomic rename)
            try:
                new_dir.rename(target_dir)
            except OSError as e:
                print(f"Hotswap Fail (Activate): {e}")
                # Restore old if new failed
                if trash_dir.exists():
                    trash_dir.rename(target_dir)
            
            # 3. Delete trash
            if trash_dir.exists():
                shutil.rmtree(trash_dir)

    # Cleanup build root
    if build_root.exists():
        shutil.rmtree(build_root)

    if count > 0:
        notify.send(
            "ZenOS Conductor",
            f"Forest Regenerated (Hotswap). Planted {count} tracks.",
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