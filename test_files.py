#!/usr/bin/env python3
"""
Validation script for sample_entities.json

This script reads entities from sample_entities.json, adds the required
entity_prefix (organization/government/federal), and validates each entity
using NES's entity_from_dict function.

Usage:
    cd services/nes
    poetry run python test_files.py
"""

import json
import sys
from pathlib import Path

from nes.core.utils.entity_utils import entity_from_dict


def main():
    # Path to the sample entities file (in the same directory)
    sample_file = Path("sample_entities.json")
    
    if not sample_file.exists():
        print(f"Error: {sample_file} not found")
        sys.exit(1)
    
    # Read the sample entities
    with open(sample_file, "r", encoding="utf-8") as f:
        entities = json.load(f)
    
    print(f"Loaded {len(entities)} entities from {sample_file.name}")
    print("-" * 80)
    
    # Track validation results
    valid_count = 0
    invalid_count = 0
    errors = []
    
    # Validate each entity
    for i, entity_data in enumerate(entities, 1):
        # Add the entity_prefix
        entity_data["entity_prefix"] = "organization/government/federal"
        
        try:
            # Validate using NES's entity_from_dict
            entity = entity_from_dict(entity_data)
            valid_count += 1
            print(f"✓ [{i}/{len(entities)}] Valid: {entity_data.get('name_en', 'Unknown')}")
            
        except Exception as e:
            invalid_count += 1
            error_msg = f"✗ [{i}/{len(entities)}] Invalid: {entity_data.get('name_en', 'Unknown')}"
            print(error_msg)
            print(f"  Error: {str(e)}")
            errors.append({
                "index": i,
                "name": entity_data.get("name_en", "Unknown"),
                "error": str(e)
            })
    
    # Print summary
    print("-" * 80)
    print(f"\nValidation Summary:")
    print(f"  Total entities: {len(entities)}")
    print(f"  Valid: {valid_count}")
    print(f"  Invalid: {invalid_count}")
    
    if errors:
        print(f"\nErrors encountered:")
        for error in errors:
            print(f"  [{error['index']}] {error['name']}: {error['error']}")
        sys.exit(1)
    else:
        print("\n✓ All entities are valid!")
        sys.exit(0)


if __name__ == "__main__":
    main()
