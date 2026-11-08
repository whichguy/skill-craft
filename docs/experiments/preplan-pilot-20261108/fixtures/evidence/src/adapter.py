"""Installed local adapter 2.3. Public interface: apply(db_path, rows).

The existing single-row client is covered; the batch failure contract has not
been characterized by this application. This module is available for inspection.
"""
import sqlite3

VERSION = "2.3"

def apply(db_path, rows):
    with sqlite3.connect(db_path) as db:
        db.execute("CREATE TABLE IF NOT EXISTS inventory (sku TEXT PRIMARY KEY, quantity INTEGER)")
        for row in rows:
            if not isinstance(row["quantity"], int) or row["quantity"] < 0:
                raise ValueError("invalid quantity")
            db.execute("INSERT OR REPLACE INTO inventory VALUES (?, ?)", (row["sku"], row["quantity"]))
            db.commit()
    return {"accepted": len(rows)}
