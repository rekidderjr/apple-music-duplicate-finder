#!/usr/bin/env python3
"""
evaluate_duplicates.py - Evaluates duplicate tracks in Apple Music Library to determine which one to keep

This script analyzes duplicate entries found by analyze_library.py and provides criteria
for determining which duplicate is more valid or higher quality to keep.
"""

import os
import sys
import json
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
import argparse

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
        with open(duplicates_path, 'r') as f:
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
    
    for group_id, duplicate_group in duplicates.items():
        evaluated_group = []
        
        for track in duplicate_group:
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
    with open(output_path, 'w') as f:
        json.dump(evaluated_duplicates, f, indent=2)
    print(f"Evaluation saved to {output_path}")

def generate_html_report(evaluated_duplicates, output_path):
    """Generate an HTML report for the evaluated duplicates."""
    html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Apple Music Duplicate Evaluation</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif;
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
    <p>Generated on: """ + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + """</p>
    <p>Total duplicate groups: """ + str(len(evaluated_duplicates)) + """</p>
    
    <div id="duplicate-groups">
"""

    for group_id, tracks in evaluated_duplicates.items():
        if not tracks:
            continue
            
        html += f"""
        <div class="duplicate-group">
            <h2>Duplicate Group {group_id}</h2>
            <h3>{tracks[0]['Name']} - {tracks[0]['Artist']}</h3>
"""
        
        for track in tracks:
            track_class = "track keep" if track.get('Recommendation') == 'KEEP' else "track remove"
            rec_class = "recommendation keep-rec" if track.get('Recommendation') == 'KEEP' else "recommendation remove-rec"
            
            html += f"""
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
                html += f"""
                    <div class="criteria-item"><strong>{key}:</strong> {value}</div>
"""
            
            html += """
                </div>
            </div>
"""
        
        html += """
        </div>
"""
    
    html += """
    </div>
</body>
</html>
"""
    
    with open(output_path, 'w') as f:
        f.write(html)
    print(f"HTML report saved to {output_path}")

def main():
    parser = argparse.ArgumentParser(description='Evaluate duplicate tracks in Apple Music Library')
    parser.add_argument('--library', default='data/Library.xml', help='Path to Apple Music Library XML file')
    parser.add_argument('--duplicates', default='output/duplicates.json', help='Path to duplicates JSON file')
    parser.add_argument('--output', default='output/evaluation.json', help='Path to save evaluation results')
    parser.add_argument('--html', default='output/evaluation_report.html', help='Path to save HTML report')
    
    args = parser.parse_args()
    
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

if __name__ == "__main__":
    main()
