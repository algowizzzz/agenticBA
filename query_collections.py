from pymongo import MongoClient
import json
client = MongoClient("mongodb://localhost:27017/")
db = client["earnings_transcripts"]
print("Collections:")
for col in db.list_collection_names():
    print(f"- {col}: {db[col].count_documents({})} documents")
print("
Analyzing document summaries...")
summaries = list(db.document_summaries.find())
print(f"Total document summaries: {len(summaries)}")
doc_ids = [s.get("document_id") for s in summaries if "document_id" in s]
print(f"Documents with summaries: {len(doc_ids)}")
cat_summary = {}
for doc_id in doc_ids:
    doc = db.transcripts.find_one({"document_id": doc_id})
    if doc and "category_id" in doc:
        cat_id = doc["category_id"]
        if cat_id not in cat_summary:
            cat_summary[cat_id] = []
        cat_summary[cat_id].append(doc_id)
print("
Categories with document summaries:")
for cat_id, docs in cat_summary.items():
    print(f"- {cat_id}: {len(docs)} documents with summaries")
top_cats = sorted(cat_summary.items(), key=lambda x: len(x[1]), reverse=True)[:3]
print("
Top 3 categories with most summaries:")
for cat_id, docs in top_cats:
    print(f"Category: {cat_id} - {len(docs)} documents")
    sample_docs = list(db.transcripts.find({"category_id": cat_id, "document_id": {"$in": docs[:3]}}, {"document_id": 1, "date": 1, "quarter": 1, "fiscal_year": 1, "_id": 0}))
    print("Sample documents:"),
    for doc in sample_docs:
        print(f"  * {json.dumps(doc, default=str)}")
