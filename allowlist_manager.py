#!/usr/bin/env python3
"""
allowlist_manager.py - Simple UI for managing the allowlist of intentional duplicates

This script provides a user-friendly interface to select duplicate files and manage
which duplicates should be ignored in future runs.
"""

import os
import sys
import glob
import json
import argparse
from datetime import datetime

def find_duplicate_json_files(output_dir='output'):
    """Find all metadata_duplicates JSON files in the output directory."""
    # First check for the standard non-timestamped file
    standard_file = f"{output_dir}/metadata_duplicates.json"
    if os.path.exists(standard_file):
        return [standard_file]
    
    # Fall back to timestamped files if standard file doesn't exist
    json_files = glob.glob(f"{output_dir}/metadata_duplicates_*.json")
    return sorted(json_files, reverse=True)  # Most recent first

def select_json_file_ui():
    """Interactive UI to select a JSON file from available options."""
    json_files = find_duplicate_json_files()
    
    if not json_files:
        print("No duplicate JSON files found in the output directory.")
        print("Please run analyze_library.py first to generate duplicate reports.")
        sys.exit(1)
    
    print("\nAvailable duplicate files:")
    for i, file_path in enumerate(json_files):
        # Extract timestamp from filename
        import re
        timestamp_match = re.search(r'(\d{8}_\d{6})', file_path)
        timestamp = timestamp_match.group(1) if timestamp_match else "Unknown"
        
        # Try to get file creation time
        try:
            ctime = datetime.fromtimestamp(os.path.getctime(file_path))
            time_str = ctime.strftime("%Y-%m-%d %H:%M:%S")
        except:
            time_str = "Unknown time"
        
        print(f"{i+1}. {os.path.basename(file_path)} (Created: {time_str})")
    
    while True:
        try:
            choice = input("\nSelect a file number (or press Enter for most recent): ")
            if choice.strip() == "":
                return json_files[0]  # Return the most recent file
            
            choice_idx = int(choice) - 1
            if 0 <= choice_idx < len(json_files):
                return json_files[choice_idx]
            else:
                print(f"Please enter a number between 1 and {len(json_files)}")
        except ValueError:
            print("Please enter a valid number")

def main():
    parser = argparse.ArgumentParser(description='Manage allowlist for Apple Music duplicates')
    parser.add_argument('--allowlist-path', default='output/allowlist.json', 
                        help='Path to allowlist JSON file (default: output/allowlist.json)')
    parser.add_argument('--text-ui', action='store_true', 
                        help='Use text-based UI instead of arrow-key UI')
    
    args = parser.parse_args()
    
    # Select the duplicates file
    duplicates_file = select_json_file_ui()
    print(f"Selected: {duplicates_file}")
    
    # Run the appropriate UI
    if args.text_ui:
        # Import the function from evaluate_duplicates.py
        from evaluate_duplicates import interactive_allowlist_manager
        interactive_allowlist_manager(duplicates_file, args.allowlist_path)
    else:
        # Import the function from evaluate_duplicates.py
        try:
            from evaluate_duplicates import interactive_arrow_allowlist_manager
            interactive_arrow_allowlist_manager(duplicates_file, args.allowlist_path)
        except ImportError as e:
            print(f"Error importing arrow UI: {e}")
            print("Falling back to text-based UI")
            from evaluate_duplicates import interactive_allowlist_manager
            interactive_allowlist_manager(duplicates_file, args.allowlist_path)

if __name__ == "__main__":
    main()
