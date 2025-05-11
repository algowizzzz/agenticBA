import chromadb
import json
from sentence_transformers import SentenceTransformer
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Constants
CHROMA_PERSIST_DIR = "./chroma_db_persist"
COLLECTION_NAME = "summary_enhanced_embeddings"
# EMBEDDING_MODEL = "all-mpnet-base-v2"  # This model has 768 dimensions
EMBEDDING_MODEL = "all-MiniLM-L6-v2"  # This model has 384 dimensions, same as original collection

# Load ticker mapping for better display
with open("ticker_uuid_mapping.txt", "r") as f:
    content = f.read().strip()
    if not content.startswith("{"):
        content = "{" + content.split("{")[1]
    ticker_mapping = json.loads(content)

# Create reverse mapping
uuid_to_ticker = {v: k for k, v in ticker_mapping.items() if v != k}

def get_display_id(category_id):
    """Convert UUID to ticker if applicable"""
    return uuid_to_ticker.get(category_id, category_id)

def run_simple_search(query, n_results=10):
    """Run a search without metadata filters"""
    # Initialize embedding model
    logger.info(f"Loading embedding model: {EMBEDDING_MODEL}")
    embedding_model = SentenceTransformer(EMBEDDING_MODEL)
    
    # Connect to ChromaDB
    logger.info(f"Connecting to ChromaDB at {CHROMA_PERSIST_DIR}")
    chroma_client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
    
    # Get collection
    collection = chroma_client.get_collection(name=COLLECTION_NAME)
    
    # Encode query
    logger.info(f"Encoding query: {query}")
    query_embedding = embedding_model.encode(query).tolist()
    
    # Run the search
    logger.info(f"Running search with n_results={n_results}")
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results,
        include=["metadatas", "documents", "distances"]
    )
    
    # Print results
    print(f"\n--- Search Results for: '{query}' ---")
    
    if results and results.get('ids') and results.get('ids')[0]:
        for i, doc_id in enumerate(results['ids'][0]):
            metadata = results['metadatas'][0][i]
            doc_type = metadata.get('document_type', 'unknown')
            category_id = metadata.get('category_id', 'Unknown')
            ticker = metadata.get('ticker', get_display_id(category_id))
            doc_name = metadata.get('document_name', 'Unknown')
            distance = results['distances'][0][i] if 'distances' in results else 1.0
            
            print(f"\n{i+1}. [{ticker}] ", end="")
            
            if doc_type == 'summary':
                print(f"Summary of {doc_name}")
            elif doc_type == 'category_summary':
                print(f"Company Overview")
            elif doc_type == 'content_chunk':
                print(f"{doc_name} (Chunk {metadata.get('chunk_index', '?')})")
            else:
                print(f"{doc_name}")
                
            print(f"   Type: {doc_type}")
            print(f"   Relevance Score: {1 - distance:.4f}")  # Convert distance to similarity
            
            # Show document content preview
            if 'documents' in results and results['documents'][0][i]:
                content = results['documents'][0][i]
                preview = content[:200] + "..." if len(content) > 200 else content
                print(f"   Preview: {preview}")
            
            # Print additional metadata
            for key, value in metadata.items():
                if key not in ['category_id', 'document_name', 'ticker', 'document_type', 'chunk_index', 'source_document_id']:
                    print(f"   {key}: {value}")
    else:
        print("No results found")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Test improved vector search")
    parser.add_argument("--query", type=str, default="nvidia growth in 2017", help="The search query")
    parser.add_argument("--n", type=int, default=10, help="Number of results to return")
    
    args = parser.parse_args()
    run_simple_search(args.query, args.n) 