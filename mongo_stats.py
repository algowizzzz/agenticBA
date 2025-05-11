from pymongo import MongoClient; client = MongoClient("mongodb://localhost:27017/"); db = client["earnings_transcripts"]; print(f"Transcript count: {db.transcripts.count_documents({})}
Category summary count: {db.category_summaries.count_documents({})}
Document summary count: {db.document_summaries.count_documents({})}")
