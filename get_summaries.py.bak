from pymongo import MongoClient
client = MongoClient("mongodb://localhost:27017/")
db = client["earnings_transcripts"]
ids = [doc.get("document_id") for doc in db.document_summaries.find({}, {"document_id": 1, "_id": 0})]
print("Document IDs with summaries:")
for i, doc_id in enumerate(ids, 1):
    print(f"{i}. {doc_id}")
print("
Categories for each document:")
for i, doc_id in enumerate(ids, 1):
    doc = db.transcripts.find_one({"document_id": doc_id})
    if doc:
        print(f"{i}. Document: {doc_id}, Category: {doc.get(\"category_id\")}")
