import sqlite3
import os
from pathlib import Path

def run():
    # Tìm tệp database SQLite tại thư mục gốc (thư mục cha của utils)
    script_dir = Path(__file__).parent
    db_path = script_dir.parent / "yhct_database.db"
    
    if not db_path.exists():
        print(f"Error: Khong tim thay file DB tai {db_path}")
        return
        
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        # Reset balance of User 1 to 1000000.0 (1 Million Tokens)
        cursor.execute("UPDATE users SET token_balance = 1000000.0 WHERE email = 'huynhthiencan2524@gmail.com'")
        print("Updated balance of huynhthiencan2524@gmail.com to 1,000,000.0")
        
        # Delete token history items that have huge amounts (like 3e+19)
        cursor.execute("DELETE FROM token_history WHERE amount > 1e15")
        deleted_history_count = cursor.rowcount
        print(f"Deleted {deleted_history_count} huge token history records.")
        
        # Delete payment items that have huge amounts (like 3e+19 or 1e+21)
        cursor.execute("DELETE FROM payments WHERE ABS(token_amount) > 1e15")
        deleted_payments_count = cursor.rowcount
        print(f"Deleted {deleted_payments_count} huge payment records.")
        
        # Also clean up the residual fractional transactions of the abnormal test
        cursor.execute("DELETE FROM token_history WHERE user_id = 1 AND amount = 30.00100000099995")
        cursor.execute("DELETE FROM payments WHERE user_id = 1 AND token_amount = -30.00100000099995")
        
        conn.commit()
        print("Successfully committed database cleanup.")
    except Exception as e:
        print(f"Error: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    run()
