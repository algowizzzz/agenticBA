from pymongo import MongoClient
from collections import Counter

# Connect to MongoDB
client = MongoClient("mongodb://localhost:27017/")
db = client["earnings_transcripts"]

# Get document IDs that have summaries
summaries = list(db.document_summaries.find({}, {"document_id": 1, "_id": 0}))
doc_ids = [s["document_id"] for s in summaries if "document_id" in s]
print(f"Documents with summaries: {len(doc_ids)}")

# Get which categories these documents belong to
categories = []
for doc_id in doc_ids:
    doc = db.transcripts.find_one({"document_id": doc_id}, {"category_id": 1})
    if doc and "category_id" in doc:
        categories.append(doc["category_id"])

# Count occurrences of each category
category_counts = Counter(categories)

# Print results
print("
Categories with document summaries:")
for cat_id, count in category_counts.most_common():
    print(f"- {cat_id}: {count} documents")
