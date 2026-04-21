import sqlite3
import pandas as pd
import os
from trade_log import get_connection, init_db, LOCAL_DB_PATH

def migrate_data():
    """
    Moves data from local trading_journal.db to the Cloud (Supabase or Oracle).
    """
    if not os.path.exists(LOCAL_DB_PATH):
        print(f"Error: Local database {LOCAL_DB_PATH} not found.")
        return

    print("Reading local data...")
    local_conn = sqlite3.connect(LOCAL_DB_PATH)
    df = pd.read_sql_query("SELECT * FROM trades", local_conn)
    local_conn.close()

    if df.empty:
        print("No data found in local database to migrate.")
        return

    print(f"Found {len(df)} trades. Initializing cloud database...")
    init_db()

    print("Uploading to Cloud... this may take a moment.")
    try:
        cloud_conn = get_connection()
    except Exception as e:
        print(f"❌ CRITICAL ERROR: Could not establish cloud connection. Migration aborted.\nDetails: {e}")
        return

    cursor = cloud_conn.cursor()

    # Prepare columns and placeholders
    columns = [col for col in df.columns if col != 'id'] # Let Cloud handle IDs
    col_names = ", ".join(columns)
    
    placeholders = ", ".join(["?"] * len(columns))
    query = f"INSERT INTO trades ({col_names}) VALUES ({placeholders})"

    success_count = 0
    for _, row in df.iterrows():
        try:
            values = tuple(row[columns].values)
            cursor.execute(query, values)
            success_count += 1
        except Exception as e:
            print(f"Failed to migrate trade {row.get('symbol')}: {e}")

    cloud_conn.commit()
    cloud_conn.close()
    print(f"Successfully migrated {success_count} trades to the Cloud!")

if __name__ == "__main__":
    migrate_data()