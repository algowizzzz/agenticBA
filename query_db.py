from pymongo import MongoClient; import json; client = MongoClient("mongodb://localhost:27017/"); db = client["earnings_transcripts"]; print("Database statistics:"); print(db.command("dbstats"))
