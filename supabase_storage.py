"""
supabase_storage.py
-------------------
Handles all Supabase Storage operations for screenshot management.
Falls back gracefully when storage is not configured (local dev mode).
"""
import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
if (BASE_DIR / ".env").exists():
    load_dotenv(dotenv_path=BASE_DIR / ".env", override=True)

# Read config — also supports Streamlit Cloud secrets via environment
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "")
STORAGE_BUCKET = os.getenv("SUPABASE_STORAGE_BUCKET", "trade-screenshots")

_client = None  # Lazily initialised singleton


def is_storage_available() -> bool:
    """Returns True if Supabase Storage credentials are configured."""
    return bool(SUPABASE_URL and SUPABASE_ANON_KEY)


def get_supabase_client():
    """Returns a cached Supabase client, or None if credentials are missing."""
    global _client
    if _client is not None:
        return _client
    if not is_storage_available():
        return None
    try:
        from supabase import create_client
        _client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
        return _client
    except Exception as e:
        print(f"[supabase_storage] Failed to initialise client: {e}")
        return None


def upload_screenshot(file_bytes: bytes, filename: str,
                      content_type: str = "image/png") -> Optional[str]:
    """
    Uploads a screenshot to the Supabase Storage bucket.

    Args:
        file_bytes:   Raw file bytes (from uploaded_file.getbuffer()).
        filename:     Destination filename inside the bucket.
        content_type: MIME type, e.g. 'image/png' or 'image/jpeg'.

    Returns:
        Public URL string on success, None on failure.
    """
    client = get_supabase_client()
    if client is None:
        print("[supabase_storage] Storage not available — skipping upload.")
        return None
    try:
        client.storage.from_(STORAGE_BUCKET).upload(
            path=filename,
            file=file_bytes,
            file_options={"content-type": content_type, "upsert": "true"},
        )
        public_url = client.storage.from_(STORAGE_BUCKET).get_public_url(filename)
        return public_url
    except Exception as e:
        print(f"[supabase_storage] Upload failed for '{filename}': {e}")
        return None


def delete_screenshot(file_url: str) -> bool:
    """
    Deletes a screenshot from Supabase Storage given its public URL.

    Args:
        file_url: The full public URL stored in the database.

    Returns:
        True on success, False on failure.
    """
    client = get_supabase_client()
    if client is None or not file_url:
        return False
    try:
        # Extract the filename portion after the bucket name
        marker = f"{STORAGE_BUCKET}/"
        if marker not in file_url:
            print(f"[supabase_storage] Cannot parse bucket path from URL: {file_url}")
            return False
        filename = file_url.split(marker, 1)[-1]
        client.storage.from_(STORAGE_BUCKET).remove([filename])
        return True
    except Exception as e:
        print(f"[supabase_storage] Delete failed for '{file_url}': {e}")
        return False
