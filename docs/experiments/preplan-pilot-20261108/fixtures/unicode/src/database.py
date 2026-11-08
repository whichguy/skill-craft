"""Application SQLite binding. Search implementation is not written yet."""
import sqlite3

def connect(path=":memory:"):
    return sqlite3.connect(path)
