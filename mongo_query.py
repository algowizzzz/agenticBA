from pymongo import MongoClient

import json
from datetime import datetime

# Connect to MongoDB
client = MongoClient("mongodb://localhost:27017/")
db = client["earnings_transcripts"]

# Print basic counts
print(f"Transcript documents: {db.transcripts.count_documents({})}")
print(f"Category summaries: {db.category_summaries.count_documents({})}")
print(f"Document summaries: {db.document_summaries.count_documents({})}")