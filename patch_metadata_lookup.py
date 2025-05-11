#!/usr/bin/env python3
"""
Patch script to modify the metadata lookup tool and fix category ID mapping issues.
This script should be run from the project root directory.
"""

import re
import os
import fileinput
import shutil
from pathlib import Path

def backup_file(file_path):
    """Create a backup of the original file."""
    backup_path = file_path + ".bak"
    shutil.copy2(file_path, backup_path)
    print(f"Created backup at {backup_path}")
    return backup_path

def patch_metadata_lookup_tool():
    """Modify the tool4_metadata_lookup.py file to handle ticker/UUID mapping."""
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
    import_replacement = r"from .config import sanitize_json_response\nfrom .category_id_mapping import normalize_category_id, get_uuid_for_ticker, get_ticker_for_uuid"
    
    modified_content = re.sub(import_pattern, import_replacement, content, flags=re.MULTILINE)
    
    # Modify the query processing logic to use the mapping function
    # Find where category ID is determined
    cat_id_pattern = r"(chosen_cat_id = None.*?)final_results\["relevant_category_id"\] = chosen_cat_id"
    
    # Add normalization logic
    normalization_code = r"\1# Normalize the category ID to ensure consistent format (prefer ticker over UUID)\n    chosen_cat_id = normalize_category_id(chosen_cat_id)\n    final_results[\"relevant_category_id\"] = chosen_cat_id"
    
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
        print("\nPatch applied successfully!")
        print("The metadata lookup tool should now correctly handle ticker and UUID mappings.")
    else:
        print("\nERROR: Failed to apply patch.")
        print("Please check the error messages above and try again.")

if __name__ == "__main__":
    main()
