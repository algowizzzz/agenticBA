#!/usr/bin/env python3
"""
Script to fix the mapping issue between ticker symbols and UUIDs in the metadata lookup tool.
"""

from pymongo import MongoClient
import json
import os
from pprint import pprint

def main():
    # Connect to MongoDB
    client = MongoClient('mongodb://localhost:27017/')
    db = client['earnings_transcripts']
    
    print("\n" + "="*80)
    print("FIXING CATEGORY MAPPING ISSUES")
    print("="*80)
    
    # 1. Create and store the ticker-to-UUID mapping
    print("\nCREATING TICKER-TO-UUID MAPPING:")
    print("-"*50)
    
    # Extract the mapping from the category field and category_id field
    ticker_to_uuid_map = {}
    uuid_to_ticker_map = {}
    
    # Query documents with both fields to extract mappings
    mapping_docs = list(db.transcripts.find(
        {"category": {"$exists": True, "$ne": None}, "category_id": {"$exists": True, "$ne": None}},
        {"category": 1, "category_id": 1, "_id": 0}
    ))
    
    print(f"Analyzing {len(mapping_docs)} documents with both category and category_id fields")
    
    # Process each document to extract mappings
    for doc in mapping_docs:
        category = doc.get("category")
        category_id = doc.get("category_id")
        
        # Skip if any field is empty
        if not category or not category_id:
            continue
        
        # Check if category is a ticker (all uppercase, 1-5 chars)
        if category.isupper() and len(category) <= 5:
            # Category is ticker, category_id is UUID
            ticker_to_uuid_map[category] = category_id
            uuid_to_ticker_map[category_id] = category
    
    # Print the mappings
    print(f"Found {len(ticker_to_uuid_map)} ticker-to-UUID mappings:")
    for ticker, uuid_str in ticker_to_uuid_map.items():
        print(f"- {ticker} → {uuid_str}")
    
    # 2. Create a mapping collection in MongoDB to store this relationship
    print("\nSTORING MAPPING IN MONGODB:")
    print("-"*50)
    
    # Check if mapping collection exists
    if "category_id_mapping" in db.list_collection_names():
        print("Dropping existing category_id_mapping collection")
        db.category_id_mapping.drop()
    
    # Create new collection
    db.create_collection("category_id_mapping")
    print("Created category_id_mapping collection")
    
    # Store each mapping
    count = 0
    for ticker, uuid_str in ticker_to_uuid_map.items():
        db.category_id_mapping.insert_one({
            "ticker": ticker,
            "uuid": uuid_str,
            "description": f"Mapping between ticker symbol {ticker} and UUID {uuid_str}"
        })
        count += 1
    
    print(f"Inserted {count} mappings into category_id_mapping collection")
    
    # 3. Create a simple function to use the mapping
    print("\nCREATING MAPPING FUNCTION:")
    print("-"*50)
    
    # Generate a Python function to convert between ticker and UUID
    mapping_function = f"""#!/usr/bin/env python3
\"\"\"
Functions to map between ticker symbols and UUIDs for category IDs.
\"\"\"

# Ticker to UUID mapping (ticker → uuid)
TICKER_TO_UUID = {json.dumps(ticker_to_uuid_map, indent=4)}

# UUID to ticker mapping (uuid → ticker)
UUID_TO_TICKER = {json.dumps(uuid_to_ticker_map, indent=4)}

def get_uuid_for_ticker(ticker):
    \"\"\"Get the UUID for a given ticker symbol.\"\"\"
    if not ticker:
        return None
    return TICKER_TO_UUID.get(ticker)

def get_ticker_for_uuid(uuid_str):
    \"\"\"Get the ticker symbol for a given UUID.\"\"\"
    if not uuid_str:
        return None
    return UUID_TO_TICKER.get(uuid_str)

def normalize_category_id(category_id):
    \"\"\"
    Normalize a category ID to ensure we return the ticker if available, otherwise the UUID.
    This helps resolve inconsistencies between ticker and UUID formats.
    \"\"\"
    if not category_id:
        return None
        
    # If it's a ticker already, return it
    if category_id in TICKER_TO_UUID:
        return category_id
        
    # If it's a UUID, convert to ticker if possible
    ticker = UUID_TO_TICKER.get(category_id)
    if ticker:
        return ticker
        
    # Otherwise just return what we got
    return category_id
    
# Example usage
if __name__ == "__main__":
    # Test with known values
    for ticker in TICKER_TO_UUID.keys():
        uuid_str = get_uuid_for_ticker(ticker)
        print(f"Ticker {{ticker}} → UUID {{uuid_str}}")
        
        # Convert back
        ticker_back = get_ticker_for_uuid(uuid_str)
        print(f"UUID {{uuid_str}} → Ticker {{ticker_back}}")
        print()
"""
    
    # Write the function to a file
    mapping_file_path = "category_id_mapping.py"
    with open(mapping_file_path, "w") as f:
        f.write(mapping_function)
    
    print(f"Wrote mapping functions to {mapping_file_path}")
    
    # 4. Test the function
    print("\nTESTING MAPPING FUNCTION:")
    print("-"*50)
    
    os.system(f"python {mapping_file_path}")
    
    # 5. Create a patch for the metadata lookup tool
    print("\nCREATING PATCH FOR METADATA LOOKUP TOOL:")
    print("-"*50)
    
    # Generate a patch to modify the metadata lookup tool
    patch_content = """#!/usr/bin/env python3
\"\"\"
Patch script to modify the metadata lookup tool and fix category ID mapping issues.
This script should be run from the project root directory.
\"\"\"

import re
import os
import fileinput
import shutil
from pathlib import Path

def backup_file(file_path):
    \"\"\"Create a backup of the original file.\"\"\"
    backup_path = file_path + ".bak"
    shutil.copy2(file_path, backup_path)
    print(f"Created backup at {backup_path}")
    return backup_path

def patch_metadata_lookup_tool():
    \"\"\"Modify the tool4_metadata_lookup.py file to handle ticker/UUID mapping.\"\"\"
    file_path = "langchain_tools/tool4_metadata_lookup.py"
    
    # Check if file exists
    if not os.path.exists(file_path):
        print(f"ERROR: {file_path} not found!")
        return False
    
    # Create backup
    backup_file(file_path)
    
    # Add import for the category ID mapping at the top of the file
    with open(file_path, "r") as f:
        content = f.read()
    
    # Add import statement after other imports
    import_pattern = r"from .config import sanitize_json_response.*$"
    import_replacement = r"from .config import sanitize_json_response\\nfrom .category_id_mapping import normalize_category_id, get_uuid_for_ticker, get_ticker_for_uuid"
    
    modified_content = re.sub(import_pattern, import_replacement, content, flags=re.MULTILINE)
    
    # Modify the query processing logic to use the mapping function
    # Find where category ID is determined
    cat_id_pattern = r"(chosen_cat_id = None.*?)final_results\\[\"relevant_category_id\"\\] = chosen_cat_id"
    
    # Add normalization logic
    normalization_code = r"\\1# Normalize the category ID to ensure consistent format (prefer ticker over UUID)\\n    chosen_cat_id = normalize_category_id(chosen_cat_id)\\n    final_results[\\"relevant_category_id\\"] = chosen_cat_id"
    
    modified_content = re.sub(cat_id_pattern, normalization_code, modified_content, flags=re.DOTALL)
    
    # Write modified content back to file
    with open(file_path, "w") as f:
        f.write(modified_content)
    
    print(f"Successfully patched {file_path}")
    
    # Create the mapping file in the langchain_tools directory
    mapping_dest = "langchain_tools/category_id_mapping.py"
    shutil.copy2("category_id_mapping.py", mapping_dest)
    print(f"Copied mapping functions to {mapping_dest}")
    
    return True

def main():
    print("Applying patch to fix category ID mapping issues...")
    success = patch_metadata_lookup_tool()
    
    if success:
        print("\\nPatch applied successfully!")
        print("The metadata lookup tool should now correctly handle ticker and UUID mappings.")
    else:
        print("\\nERROR: Failed to apply patch.")
        print("Please check the error messages above and try again.")

if __name__ == "__main__":
    main()
"""
    
    # Write the patch to a file
    patch_file_path = "patch_metadata_lookup.py"
    with open(patch_file_path, "w") as f:
        f.write(patch_content)
    
    print(f"Wrote patch script to {patch_file_path}")
    
    print("\n" + "="*80)
    print("FIX PREPARATION COMPLETE")
    print("="*80)
    print("\nTo apply the fix:")
    print("1. Run 'python patch_metadata_lookup.py' to patch the metadata lookup tool")
    print("2. Restart the application to use the updated mapping")
    print("\n")

if __name__ == "__main__":
    main() 