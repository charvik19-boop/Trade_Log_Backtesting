import os
from pathlib import Path
from dotenv import load_dotenv
import trade_log
import socket
from urllib.parse import urlparse

def verify_environment():
    print("--- Environment Check ---")
    base_dir = Path(__file__).resolve().parent
    env_path = base_dir / ".env"
    
    if env_path.exists():
        print(f"Found .env file at: {env_path}")
        # override=True ensures that .env values take precedence over system variables
        success = load_dotenv(dotenv_path=env_path, override=True)
        if success:
            print("✅ Environment file loaded successfully.")
    else:
        print("WARNING: .env file not found in the project root.")

    print(f"Status: 🏠 LOCAL SQLite (Path: {trade_log.LOCAL_DB_PATH})")

    # Live Connection Test
    try:
        print("\nAttempting live connection test...")
        conn = trade_log.get_connection()
        print("✅ SUCCESS: Successfully connected to the database!")
        conn.close()
    except Exception as e:
        print(f"❌ CONNECTION FAILED: {e}")

if __name__ == "__main__":
    verify_environment()