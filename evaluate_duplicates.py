#!/usr/bin/env python3
"""
evaluate_duplicates.py - Evaluates duplicate tracks in Apple Music Library

This script analyzes duplicate entries found by analyze_library.py and provides criteria
for determining which duplicate is more valid or higher quality to keep.
"""

import os
import sys
import json
import glob
import xml.etree.ElementTree as ET
from datetime import datetime
import argparse

try:
    import defusedxml.ElementTree
    # Replace standard ElementTree with defusedxml for security
    ET = defusedxml.ElementTree
    print("Using defusedxml for secure XML parsing")
except ImportError:
    print("Warning: defusedxml not installed. XML parsing may be vulnerable to attacks.")
    print("Install with: pip install defusedxml")

def parse_library_xml(xml_path):
    """Parse the Apple Music Library XML file."""
    print(f"Parsing Apple Music Library XML from {xml_path}...")
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
        return root
    except ET.ParseError as e:
        print(f"Error parsing XML file: {e}")
        sys.exit(1)
    except FileNotFoundError:
        print(f"Library file not found at {xml_path}")
        print("Please export your Apple Music Library to this location.")
        sys.exit(1)

def load_duplicates(duplicates_path):
    """Load the duplicates data from the JSON file."""
    try:
        with open(duplicates_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Duplicates file not found at {duplicates_path}")
        print("Please run analyze_library.py first to generate the duplicates file.")
        sys.exit(1)

def evaluate_duplicates(root, duplicates):
    """
    Evaluate duplicate tracks to determine which one to keep.
    
    Criteria for evaluation:
    1. File existence (files that exist are preferred)
    2. File size (larger files might indicate higher quality)
    3. Bit rate (higher bit rate is better)
    4. Sample rate (higher sample rate is better)
    5. Play count (tracks played more often might be preferred)
    6. Date added (newer entries might have updated metadata)
    7. Rating (higher rated tracks might be preferred)
    """
    tracks_dict = {}
    
    # First, build a dictionary of all tracks
    for dict_elem in root.findall('.//dict'):
        track_id_elem = None
        for i, elem in enumerate(dict_elem):
            if elem.tag == 'key' and elem.text == 'Track ID':
                track_id_elem = dict_elem[i+1]
                break
        
        if track_id_elem is not None:
            track_id = track_id_elem.text
            tracks_dict[track_id] = dict_elem
    
    evaluated_duplicates = {}
    
    # Check if we're dealing with the duplicate_groups structure
    if "duplicate_groups" in duplicates:
        duplicate_groups = duplicates["duplicate_groups"]
    else:
        duplicate_groups = duplicates
    
    for group_id, duplicate_group in enumerate(duplicate_groups):
        evaluated_group = []
        
        # Handle the structure from metadata_duplicates JSON
        if "tracks" in duplicate_group:
            tracks_to_evaluate = duplicate_group["tracks"]
        else:
            tracks_to_evaluate = duplicate_group
            
        for track in tracks_to_evaluate:
            track_id = str(track['Track ID'])
            track_dict = tracks_dict.get(track_id)
            
            if track_dict is None:
                continue
                
            evaluation = {
                'Track ID': track_id,
                'Name': track.get('Name', 'Unknown'),
                'Artist': track.get('Artist', 'Unknown'),
                'Location': track.get('Location', ''),
                'Criteria': {}
            }
            
            # Check if file exists
            location = track.get('Location', '')
            if location.startswith('file://'):
                file_path = location[7:].replace('%20', ' ')
                file_exists = os.path.exists(file_path)
                evaluation['Criteria']['File Exists'] = file_exists
            
            # Extract other criteria from track_dict
            for i, elem in enumerate(track_dict):
                if elem.tag == 'key':
                    key = elem.text
                    value_elem = track_dict[i+1]
                    
                    if key == 'Size':
                        evaluation['Criteria']['File Size'] = int(value_elem.text)
                    elif key == 'Bit Rate':
                        evaluation['Criteria']['Bit Rate'] = int(value_elem.text)
                    elif key == 'Sample Rate':
                        evaluation['Criteria']['Sample Rate'] = int(value_elem.text)
                    elif key == 'Play Count':
                        evaluation['Criteria']['Play Count'] = int(value_elem.text)
                    elif key == 'Rating':
                        evaluation['Criteria']['Rating'] = int(value_elem.text)
                    elif key == 'Date Added':
                        evaluation['Criteria']['Date Added'] = value_elem.text
            
            evaluated_group.append(evaluation)
        
        # Determine which track is recommended to keep
        if evaluated_group:
            # Sort by multiple criteria
            # 1. File existence (True > False)
            # 2. Bit Rate (higher > lower)
            # 3. Sample Rate (higher > lower)
            # 4. File Size (larger > smaller)
            # 5. Play Count (higher > lower)
            # 6. Rating (higher > lower)
            # 7. Date Added (newer > older)
            
            for track in evaluated_group:
                track['Score'] = 0
                criteria = track['Criteria']
                
                # File exists is most important
                if criteria.get('File Exists', False):
                    track['Score'] += 1000
                
                # Add other criteria scores
                track['Score'] += criteria.get('Bit Rate', 0)
                track['Score'] += criteria.get('Sample Rate', 0) / 100
                track['Score'] += criteria.get('File Size', 0) / 1000000
                track['Score'] += criteria.get('Play Count', 0) * 5
                track['Score'] += criteria.get('Rating', 0) * 10
            
            # Sort by score (descending)
            evaluated_group.sort(key=lambda x: x['Score'], reverse=True)
            
            # Add recommendation
            for i, track in enumerate(evaluated_group):
                if i == 0:
                    track['Recommendation'] = 'KEEP'
                else:
                    track['Recommendation'] = 'REMOVE'
        
        evaluated_duplicates[group_id] = evaluated_group
    
    return evaluated_duplicates

def save_evaluation(evaluated_duplicates, output_path):
    """Save the evaluation results to a JSON file."""
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(evaluated_duplicates, f, indent=2)
    print(f"Evaluation saved to {output_path}")

def generate_html_report(evaluated_duplicates, output_path):
    """Generate an HTML report for the evaluated duplicates."""
    html_start = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Apple Music Duplicate Evaluation</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 
            'Open Sans', 'Helvetica Neue', sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }
        h1, h2, h3 {
            color: #333;
        }
        .duplicate-group {
            margin-bottom: 30px;
            border: 1px solid #ddd;
            border-radius: 5px;
            padding: 15px;
            background-color: #f9f9f9;
        }
        .track {
            margin-bottom: 15px;
            padding: 10px;
            border-left: 5px solid #ddd;
            background-color: white;
        }
        .keep {
            border-left-color: #4CAF50;
        }
        .remove {
            border-left-color: #F44336;
        }
        .criteria {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
            gap: 10px;
            margin-top: 10px;
        }
        .criteria-item {
            background-color: #eee;
            padding: 5px 10px;
            border-radius: 3px;
        }
        .recommendation {
            font-weight: bold;
            padding: 3px 8px;
            border-radius: 3px;
            display: inline-block;
            margin-left: 10px;
        }
        .keep-rec {
            background-color: #4CAF50;
            color: white;
        }
        .remove-rec {
            background-color: #F44336;
            color: white;
        }
    </style>
</head>
<body>
    <h1>Apple Music Duplicate Evaluation</h1>
"""

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    html_content = f"""    <p>Generated on: {timestamp}</p>
    <p>Total duplicate groups: {len(evaluated_duplicates)}</p>
    
    <div id="duplicate-groups">
"""

    for group_id, tracks in evaluated_duplicates.items():
        if not tracks:
            continue
            
        html_content += f"""
        <div class="duplicate-group">
            <h2>Duplicate Group {group_id}</h2>
            <h3>{tracks[0]['Name']} - {tracks[0]['Artist']}</h3>
"""
        
        for track in tracks:
            track_class = "track keep" if track.get('Recommendation') == 'KEEP' else "track remove"
            rec_class = "recommendation keep-rec" if track.get('Recommendation') == 'KEEP' else "recommendation remove-rec"
            
            html_content += f"""
            <div class="{track_class}">
                <div>
                    <strong>Track ID:</strong> {track['Track ID']}
                    <span class="{rec_class}">{track.get('Recommendation', '')}</span>
                </div>
                <div><strong>Location:</strong> {track['Location']}</div>
                <div><strong>Score:</strong> {track.get('Score', 0):.2f}</div>
                
                <div class="criteria">
"""
            
            for key, value in track.get('Criteria', {}).items():
                html_content += f"""
                    <div class="criteria-item"><strong>{key}:</strong> {value}</div>
"""
            
            html_content += """
                </div>
            </div>
"""
        
        html_content += """
        </div>
"""
    
    html_end = """
    </div>
</body>
</html>
"""
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_start + html_content + html_end)
    print(f"HTML report saved to {output_path}")

def add_to_allowlist(track_ids, allowlist_path='output/allowlist.json', 
                    duplicate_type='metadata_duplicates'):
    """
    Add a set of track IDs to the allowlist so they won't be flagged as duplicates in future runs.
    
    Args:
        track_ids: List of track IDs to add to the allowlist
        allowlist_path: Path to the allowlist JSON file
        duplicate_type: Type of duplicate ('metadata_duplicates' or 'location_duplicates')
    """
    # Load existing allowlist
    if os.path.exists(allowlist_path):
        try:
            with open(allowlist_path, 'r', encoding='utf-8') as f:
                allowlist = json.load(f)
        except json.JSONDecodeError:
            allowlist = {'metadata_duplicates': [], 'location_duplicates': []}
    else:
        allowlist = {'metadata_duplicates': [], 'location_duplicates': []}
    
    # Ensure the duplicate type exists in the allowlist
    if duplicate_type not in allowlist:
        allowlist[duplicate_type] = []
    
    # Sort track IDs to ensure consistent comparison
    sorted_track_ids = sorted(track_ids)
    
    # Check if this set of track IDs is already in the allowlist
    for existing_ids in allowlist[duplicate_type]:
        if sorted(existing_ids) == sorted_track_ids:
            print("These tracks are already in the allowlist.")
            return
    
    # Add to allowlist
    allowlist[duplicate_type].append(sorted_track_ids)
    
    # Save updated allowlist
    with open(allowlist_path, 'w', encoding='utf-8') as f:
        json.dump(allowlist, f, indent=2)
    
    print(f"Added tracks {', '.join(track_ids)} to the allowlist.")
    print("These tracks will be ignored in future duplicate detection runs.")

def interactive_allowlist_manager(duplicates_path, allowlist_path='output/allowlist.json'):
    """
    Interactive command-line interface to manage the allowlist.
    
    Args:
        duplicates_path: Path to the duplicates JSON file
        allowlist_path: Path to the allowlist JSON file
    """
    # Load duplicates
    duplicates = load_duplicates(duplicates_path)
    
    # Determine the structure of the duplicates file
    if "duplicate_groups" in duplicates:
        duplicate_groups = duplicates["duplicate_groups"]
        duplicate_type = 'metadata_duplicates'
    else:
        duplicate_groups = duplicates
        duplicate_type = 'location_duplicates'
    
    print("\nAllowlist Manager")
    print("================")
    print("This tool helps you mark duplicates as intentional so they won't be flagged in future runs.")
    print(f"Found {len(duplicate_groups)} duplicate groups.")
    
    for i, group in enumerate(duplicate_groups):
        print(f"\nGroup {i+1}:")
        
        # Handle the structure from metadata_duplicates JSON
        if "tracks" in group:
            tracks = group["tracks"]
            if "name" in group and "artist" in group:
                print(f"  {group['name']} - {group['artist']}")
        else:
            tracks = group
        
        for j, track in enumerate(tracks):
            print(f"  {j+1}. {track.get('Name', 'Unknown')} - {track.get('Artist', 'Unknown')}")
            print(f"     Location: {track.get('Location', 'Unknown')}")
            print(f"     Track ID: {track.get('Track ID', 'Unknown')}")
        
        choice = input("\nAdd this group to allowlist? (y/n/q to quit): ").lower()
        if choice == 'q':
            break
        elif choice == 'y':
            track_ids = [track.get('Track ID') for track in tracks]
            add_to_allowlist(track_ids, allowlist_path, duplicate_type)
    
    print("\nAllowlist management complete.")

def interactive_arrow_allowlist_manager(duplicates_path, allowlist_path='output/allowlist.json'):
    """
    Interactive arrow-key based interface to manage the allowlist.
    
    Args:
        duplicates_path: Path to the duplicates JSON file
        allowlist_path: Path to the allowlist JSON file
    """
    try:
        import curses
        from curses import wrapper
    except ImportError:
        print("Curses library not available. Falling back to text-based interface.")
        interactive_allowlist_manager(duplicates_path, allowlist_path)
        return

    # Load duplicates
    duplicates = load_duplicates(duplicates_path)

    # Determine the structure of the duplicates file
    if "duplicate_groups" in duplicates:
        duplicate_groups = duplicates["duplicate_groups"]
        duplicate_type = 'metadata_duplicates'
    else:
        duplicate_groups = duplicates
        duplicate_type = 'location_duplicates'

    def main_curses(stdscr):
        # Clear screen
        stdscr.clear()
        curses.curs_set(0)  # Hide cursor

        # Enable color if available
        if curses.has_colors():
            curses.start_color()
            curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLUE)  # Selected item
            curses.init_pair(2, curses.COLOR_GREEN, curses.COLOR_BLACK)  # Marked item
            curses.init_pair(3, curses.COLOR_YELLOW, curses.COLOR_BLACK)  # Header
        
        # Get screen dimensions
        max_y, max_x = stdscr.getmaxyx()
        
        # Initialize variables
        current_pos = 0
        marked_groups = set()
        top_line = 0

        # Main loop
        while True:
            stdscr.clear()

            # Display header
            header = "Apple Music Duplicate Allowlist Manager"
            stdscr.addstr(0, 0, header, curses.color_pair(3) if curses.has_colors() else curses.A_BOLD)
            stdscr.addstr(1, 0, "=" * min(len(header), max_x-1))
            msg = f"Found {len(duplicate_groups)} duplicate groups. "
            msg += "Use arrow keys to navigate, SPACE to mark/unmark, ENTER to save."
            stdscr.addstr(2, 0, msg)

            # Display groups
            display_lines = max_y - 6  # Reserve lines for header and footer
            for i in range(top_line, min(top_line + display_lines, len(duplicate_groups))):
                group = duplicate_groups[i]
                y_pos = i - top_line + 4  # Start after header
                
                # Handle the structure from metadata_duplicates JSON
                if "tracks" in group:
                    tracks = group["tracks"]
                    if "name" in group and "artist" in group:
                        group_name = f"{group['name']} - {group['artist']}"
                    else:
                        group_name = f"Group {i+1}"
                else:
                    tracks = group
                    group_name = f"Group {i+1}"
                
                # Format display string
                display_str = f"{i+1}. {group_name} ({len(tracks)} tracks)"
                
                # Highlight current position or mark selected
                if i == current_pos:
                    attr = curses.color_pair(1) if curses.has_colors() else curses.A_REVERSE
                elif i in marked_groups:
                    attr = curses.color_pair(2) if curses.has_colors() else curses.A_BOLD
                else:
                    attr = curses.A_NORMAL

                # Add marker for selected items
                prefix = "[*] " if i in marked_groups else "[ ] "

                # Display the line
                stdscr.addstr(y_pos, 0, prefix + display_str[:max_x-5], attr)

                # If this is the current position, show track details
                if i == current_pos and y_pos + 1 < max_y - 1:
                    for j, track in enumerate(tracks[:2]):  # Show first 2 tracks
                        if y_pos + j + 1 < max_y - 1:
                            track_info = f"    - {track.get('Name', 'Unknown')}"
                            track_info += f" ({track.get('Location', 'Unknown')})"
                            stdscr.addstr(y_pos + j + 1, 0, track_info[:max_x-1])

                    if len(tracks) > 2 and y_pos + 3 < max_y - 1:
                        stdscr.addstr(y_pos + 3, 0, f"    ... and {len(tracks) - 2} more tracks")

            # Display footer
            footer_y = max_y - 1
            footer = "↑/↓: Navigate | SPACE: Mark/Unmark | ENTER: Save | q: Quit"
            stdscr.addstr(footer_y, 0, footer, 
                         curses.A_BOLD if curses.has_colors() else curses.A_NORMAL)

            # Refresh the screen
            stdscr.refresh()

            # Get user input
            key = stdscr.getch()

            # Process input
            if key == curses.KEY_UP and current_pos > 0:
                current_pos -= 1
                if current_pos < top_line:
                    top_line = current_pos
            elif key == curses.KEY_DOWN and current_pos < len(duplicate_groups) - 1:
                current_pos += 1
                if current_pos >= top_line + display_lines:
                    top_line = current_pos - display_lines + 1
            elif key == ord(' '):  # Space key
                if current_pos in marked_groups:
                    marked_groups.remove(current_pos)
                else:
                    marked_groups.add(current_pos)
            elif key == ord('\n'):  # Enter key
                break
            elif key == ord('q'):
                return  # Exit without saving

        # Save marked groups to allowlist
        if marked_groups:
            # Load existing allowlist
            if os.path.exists(allowlist_path):
                try:
                    with open(allowlist_path, 'r', encoding='utf-8') as f:
                        allowlist = json.load(f)
                except json.JSONDecodeError:
                    allowlist = {'metadata_duplicates': [], 'location_duplicates': []}
            else:
                allowlist = {'metadata_duplicates': [], 'location_duplicates': []}

            # Ensure the duplicate type exists in the allowlist
            if duplicate_type not in allowlist:
                allowlist[duplicate_type] = []

            # Add marked groups to allowlist
            for idx in marked_groups:
                group = duplicate_groups[idx]

                # Handle the structure from metadata_duplicates JSON
                if "tracks" in group:
                    tracks = group["tracks"]
                else:
                    tracks = group

                # Get track IDs and add to allowlist
                track_ids = sorted([track.get('Track ID') for track in tracks])

                # Check if already in allowlist
                already_exists = False
                for existing_ids in allowlist[duplicate_type]:
                    if sorted(existing_ids) == track_ids:
                        already_exists = True
                        break

                if not already_exists:
                    allowlist[duplicate_type].append(track_ids)

            # Save updated allowlist
            with open(allowlist_path, 'w', encoding='utf-8') as f:
                json.dump(allowlist, f, indent=2)

            # Show confirmation message
            stdscr.clear()
            stdscr.addstr(0, 0, f"Added {len(marked_groups)} groups to the allowlist.", curses.A_BOLD)
            stdscr.addstr(1, 0, "These duplicates will be ignored in future runs.")
            stdscr.addstr(3, 0, "Press any key to continue...")
            stdscr.refresh()
            stdscr.getch()
    
    # Run the curses application
    wrapper(main_curses)

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
        except Exception:
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
    parser = argparse.ArgumentParser(description='Evaluate duplicate tracks in Apple Music Library')
    parser.add_argument('--library', default='data/Library.xml', 
                       help='Path to Apple Music Library XML file')
    parser.add_argument('--duplicates', help='Path to duplicates JSON file')
    parser.add_argument('--output', default='output/evaluation.json', 
                       help='Path to save evaluation results')
    parser.add_argument('--html', default='output/evaluation_report.html', 
                       help='Path to save HTML report')
    parser.add_argument('--allowlist', action='store_true', 
                       help='Run in allowlist management mode')
    parser.add_argument('--allowlist-path', default='output/allowlist.json', 
                       help='Path to allowlist JSON file')
    parser.add_argument('--arrow-ui', action='store_true', 
                       help='Use arrow-key based UI for allowlist management')
    parser.add_argument('--select', action='store_true', 
                       help='Show UI to select duplicates JSON file')

    args = parser.parse_args()

    # If --select is specified or no duplicates file is provided, show the selection UI
    if args.select or not args.duplicates:
        args.duplicates = select_json_file_ui()
        print(f"Selected: {args.duplicates}")
    # If no duplicates file is specified, use the default non-timestamped file
    elif not args.duplicates:
        args.duplicates = 'output/metadata_duplicates.json'

    # Check if we're in allowlist management mode
    if args.allowlist:
        if args.arrow_ui:
            interactive_arrow_allowlist_manager(args.duplicates, args.allowlist_path)
        else:
            interactive_allowlist_manager(args.duplicates, args.allowlist_path)
        return

    # Ensure output directory exists
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    os.makedirs(os.path.dirname(args.html), exist_ok=True)

    # Parse library XML
    root = parse_library_xml(args.library)

    # Load duplicates
    duplicates = load_duplicates(args.duplicates)

    # Evaluate duplicates
    evaluated_duplicates = evaluate_duplicates(root, duplicates)

    # Save evaluation results
    save_evaluation(evaluated_duplicates, args.output)

    # Generate HTML report
    generate_html_report(evaluated_duplicates, args.html)

    print("Evaluation complete!")
    print(f"JSON results saved to: {args.output}")
    print(f"HTML report saved to: {args.html}")
    print("\nTo add duplicates to the allowlist (so they won't be flagged in future runs):")
    print(f"python evaluate_duplicates.py --allowlist --duplicates {args.duplicates}")
    print("Or use the arrow-key based interface:")
    print(f"python evaluate_duplicates.py --allowlist --arrow-ui --duplicates {args.duplicates}")

if __name__ == "__main__":
    main()
