import unittest
from src import database

class Baseline(unittest.TestCase):
    def test_application_connection(self):
        with database.connect() as db:
            self.assertEqual(db.execute("select 1").fetchone(), (1,))

if __name__ == "__main__": unittest.main()
