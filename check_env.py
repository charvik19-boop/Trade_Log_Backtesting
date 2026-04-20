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

    oracle_dsn = os.getenv("ORACLE_DSN")
    db_url = os.getenv("DATABASE_URL")
    supabase_mode = os.getenv("SUPABASE_MODE", "DIRECT").upper()
    force_local = os.getenv("FORCE_LOCAL", "False").lower() == "true"

    print("\n--- Connection Strings Status ---")
    if force_local:
        print(f"Status: 🏠 LOCAL MODE ENABLED (Path: {trade_log.LOCAL_DB_PATH})")
    elif oracle_dsn:
        # Masking password for security while confirming presence
        masked_dsn = oracle_dsn.split('@')[0].split('/')[0] + ":****@" + oracle_dsn.split('@')[-1]
        print(f"Oracle DSN: {masked_dsn}")
    elif db_url:
        print(f"Supabase Mode: 🚀 {supabase_mode}")
        masked_url = db_url.split('@')[0].rsplit(':', 1)[0] + ":****@" + db_url.split('@')[-1]
        print(f"Postgres URL: {masked_url}")
    else:
        print(f"Status: Falling back to Local SQLite (Path: {trade_log.LOCAL_DB_PATH})")

    # Live Connection Test
    try:
        # Diagnostic: Test DNS resolution using professional URL parsing
        if db_url:
            parsed = urlparse(db_url)
            hostname = parsed.hostname
            print(f"Checking DNS for: {hostname}...")
            try:
                ip = socket.gethostbyname(hostname)
                print(f"✅ DNS Resolved: {ip}")
            except socket.gaierror:
                print(f"❌ DNS ERROR: Could not resolve '{hostname}'.")
                print("\n   [DIAGNOSTIC STEPS]")
                print(f"   1. IPv4 ALERT: The direct host '{hostname}' is likely IPv6-only.")
                print("      FIX: Use the 'Connection Pooler' host (port 6543) from Supabase Settings.")
                print(f"   2. Log in to Supabase and check if project '{hostname.split('.')[1]}' is PAUSED.")
                print("   3. Verify your internet connection or try 'ipconfig /flushdns' in terminal.")

        print("\nAttempting live connection test...")
        conn = trade_log.get_connection()
        print("✅ SUCCESS: Successfully connected to the database!")
        conn.close()
    except Exception as e:
        print(f"❌ CONNECTION FAILED: {e}")

if __name__ == "__main__":
    verify_environment()