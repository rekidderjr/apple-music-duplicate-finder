#!/usr/bin/env python3
"""
Apple Music Library Duplicate Finder

This script analyzes an Apple Music Library.XML file to identify duplicate tracks
based on metadata and file paths.
"""

import os
import sys
import xml.etree.ElementTree as ET
import plistlib
import datetime
import json
from collections import defaultdict
import argparse

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Find duplicate tracks in Apple Music Library')
    parser.add_argument('--input', '-i', default='data/Library.xml',
                        help='Path to Library.xml file (default: data/Library.xml)')
    parser.add_argument('--output', '-o', default='output',
                        help='Directory for output reports (default: output)')
    return parser.parse_args()

def ensure_directory_exists(directory):
    """Create directory if it doesn't exist."""
    if not os.path.exists(directory):
        os.makedirs(directory)
        print(f"Created directory: {directory}")

def load_library(file_path):
    """Load and parse the Apple Music Library.XML file."""
    if not os.path.exists(file_path):
        print(f"Error: Library file not found at {file_path}")
        print("Please export your Apple Music Library and place it in the specified location.")
        sys.exit(1)
    
    print(f"Loading library from {file_path}...")
    try:
        with open(file_path, 'rb') as file:
            library = plistlib.load(file)
        return library
    except Exception as e:
        print(f"Error loading library: {e}")
        sys.exit(1)

def extract_tracks(library):
    """Extract track information from the library."""
    if 'Tracks' not in library:
        print("Error: No tracks found in the library file.")
        sys.exit(1)
    
    return library['Tracks']

def find_duplicates_by_metadata(tracks):
    """Find tracks with identical metadata but different file paths."""
    # Group by a combination of metadata fields
    metadata_groups = defaultdict(list)
    
    for track_id, track in tracks.items():
        # Skip tracks without location
        if 'Location' not in track:
            continue
        
        # Extract file extension from location
        location = track.get('Location', '')
        file_extension = os.path.splitext(location)[1].lower()
        
        # Create a metadata key using relevant fields including file extension
        metadata_key = (
            track.get('Name', ''),
            track.get('Artist', ''),
            track.get('Album', ''),
            track.get('Total Time', 0),
            file_extension  # Include file extension in the key
        )
        
        metadata_groups[metadata_key].append({
            'Track ID': track_id,
            'Name': track.get('Name', 'Unknown'),
            'Artist': track.get('Artist', 'Unknown'),
            'Album': track.get('Album', 'Unknown'),
            'Location': track.get('Location', ''),
            'Play Count': track.get('Play Count', 0),
            'Date Added': track.get('Date Added', ''),
            'File Extension': file_extension
        })
    
    # Filter for groups with more than one track
    duplicates = {key: tracks for key, tracks in metadata_groups.items() if len(tracks) > 1}
    return duplicates

def find_duplicates_by_location(tracks):
    """Find multiple entries pointing to the same file."""
    location_groups = defaultdict(list)
    
    for track_id, track in tracks.items():
        if 'Location' not in track:
            continue
        
        location = track['Location']
        location_groups[location].append({
            'Track ID': track_id,
            'Name': track.get('Name', 'Unknown'),
            'Artist': track.get('Artist', 'Unknown'),
            'Album': track.get('Album', 'Unknown'),
            'Play Count': track.get('Play Count', 0),
            'Date Added': track.get('Date Added', '')
        })
    
    # Filter for groups with more than one track
    duplicates = {loc: tracks for loc, tracks in location_groups.items() if len(tracks) > 1}
    return duplicates

def generate_report(metadata_duplicates, location_duplicates, output_dir):
    """Generate reports for duplicate tracks."""
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Report for metadata duplicates
    metadata_report = {
        'report_type': 'Duplicate Tracks with Different Locations',
        'generated_at': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'total_duplicate_groups': len(metadata_duplicates),
        'duplicate_groups': []
    }
    
    # CSV data for metadata duplicates
    metadata_csv_rows = []
    metadata_csv_rows.append(['Group ID', 'Track ID', 'Name', 'Artist', 'Album', 'Duration (ms)', 'File Extension', 'Play Count', 'Date Added', 'Location'])
    
    group_id = 1
    for key, tracks in metadata_duplicates.items():
        # Convert any datetime objects in tracks to strings
        processed_tracks = []
        for track in tracks:
            processed_track = {}
            for k, v in track.items():
                if isinstance(v, datetime.datetime):
                    processed_track[k] = v.strftime("%Y-%m-%d %H:%M:%S")
                else:
                    processed_track[k] = v
            processed_tracks.append(processed_track)
            
            # Add to CSV data
            metadata_csv_rows.append([
                group_id,
                track['Track ID'],
                track['Name'],
                track['Artist'],
                track['Album'],
                key[3],  # Duration from the key tuple
                track.get('File Extension', ''),
                track.get('Play Count', 0),
                track.get('Date Added', ''),
                track['Location']
            ])
            
        metadata_report['duplicate_groups'].append({
            'name': key[0],
            'artist': key[1],
            'album': key[2],
            'duration': key[3],
            'file_extension': key[4],  # Add file extension to the report
            'tracks': processed_tracks
        })
        group_id += 1
    
    # Report for location duplicates
    location_report = {
        'report_type': 'Multiple Entries with Same Location',
        'generated_at': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'total_duplicate_groups': len(location_duplicates),
        'duplicate_groups': []
    }
    
    # CSV data for location duplicates
    location_csv_rows = []
    location_csv_rows.append(['Group ID', 'Track ID', 'Name', 'Artist', 'Album', 'Play Count', 'Date Added', 'Location'])
    
    group_id = 1
    for location, tracks in location_duplicates.items():
        # Convert any datetime objects in tracks to strings
        processed_tracks = []
        for track in tracks:
            processed_track = {}
            for k, v in track.items():
                if isinstance(v, datetime.datetime):
                    processed_track[k] = v.strftime("%Y-%m-%d %H:%M:%S")
                else:
                    processed_track[k] = v
            processed_tracks.append(processed_track)
            
            # Add to CSV data
            location_csv_rows.append([
                group_id,
                track['Track ID'],
                track.get('Name', 'Unknown'),
                track.get('Artist', 'Unknown'),
                track.get('Album', 'Unknown'),
                track.get('Play Count', 0),
                track.get('Date Added', ''),
                location
            ])
            
        location_report['duplicate_groups'].append({
            'location': location,
            'tracks': processed_tracks
        })
        group_id += 1
    
    # Write reports to files
    metadata_file = os.path.join(output_dir, f"metadata_duplicates_{timestamp}.json")
    location_file = os.path.join(output_dir, f"location_duplicates_{timestamp}.json")
    excel_file = os.path.join(output_dir, f"duplicates_{timestamp}.xlsx")
    
    # Write JSON reports
    with open(metadata_file, 'w') as f:
        json.dump(metadata_report, f, indent=2)
    
    with open(location_file, 'w') as f:
        json.dump(location_report, f, indent=2)
    
    # Write Excel report with multiple sheets
    try:
        import openpyxl
        from openpyxl.styles import Font, PatternFill
        
        # Create a new workbook
        wb = openpyxl.Workbook()
        
        # Create metadata duplicates sheet
        metadata_sheet = wb.active
        metadata_sheet.title = "Metadata Duplicates"
        
        # Add headers with formatting
        header_font = Font(bold=True)
        header_fill = PatternFill(start_color="DDDDDD", end_color="DDDDDD", fill_type="solid")
        
        for col_idx, header in enumerate(metadata_csv_rows[0], 1):
            cell = metadata_sheet.cell(row=1, column=col_idx, value=header)
            cell.font = header_font
            cell.fill = header_fill
        
        # Add data rows
        for row_idx, row_data in enumerate(metadata_csv_rows[1:], 2):
            for col_idx, cell_value in enumerate(row_data, 1):
                metadata_sheet.cell(row=row_idx, column=col_idx, value=cell_value)
        
        # Create location duplicates sheet
        if location_csv_rows and len(location_csv_rows) > 1:  # If we have data beyond headers
            location_sheet = wb.create_sheet(title="Location Duplicates")
            
            # Add headers with formatting
            for col_idx, header in enumerate(location_csv_rows[0], 1):
                cell = location_sheet.cell(row=1, column=col_idx, value=header)
                cell.font = header_font
                cell.fill = header_fill
            
            # Add data rows
            for row_idx, row_data in enumerate(location_csv_rows[1:], 2):
                for col_idx, cell_value in enumerate(row_data, 1):
                    location_sheet.cell(row=row_idx, column=col_idx, value=cell_value)
        
        # Create summary sheet
        summary_sheet = wb.create_sheet(title="Summary", index=0)  # Make it the first sheet
        
        # Add summary information
        summary_sheet.cell(row=1, column=1, value="Apple Music Library Duplicate Analysis")
        summary_sheet.cell(row=1, column=1).font = Font(bold=True, size=14)
        
        summary_sheet.cell(row=3, column=1, value="Analysis Date:")
        summary_sheet.cell(row=3, column=2, value=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        
        summary_sheet.cell(row=5, column=1, value="Duplicate Tracks with Different Locations:")
        summary_sheet.cell(row=5, column=2, value=len(metadata_duplicates))
        
        summary_sheet.cell(row=6, column=1, value="Multiple Entries with Same Location:")
        summary_sheet.cell(row=6, column=2, value=len(location_duplicates))
        
        # Add instructions
        summary_sheet.cell(row=8, column=1, value="Instructions:")
        summary_sheet.cell(row=9, column=1, value="• Use the tabs at the bottom to navigate between different types of duplicates")
        summary_sheet.cell(row=10, column=1, value="• 'Metadata Duplicates' shows tracks with identical metadata but different file paths")
        summary_sheet.cell(row=11, column=1, value="• 'Location Duplicates' shows multiple entries pointing to the same file")
        
        # Adjust column widths for better readability
        for sheet in wb.worksheets:
            for column in sheet.columns:
                max_length = 0
                column_letter = openpyxl.utils.get_column_letter(column[0].column)
                for cell in column:
                    if cell.value:
                        max_length = max(max_length, len(str(cell.value)))
                adjusted_width = max_length + 2
                sheet.column_dimensions[column_letter].width = min(adjusted_width, 50)  # Cap at 50 for very long paths
        
        # Save the workbook
        wb.save(excel_file)
        excel_created = True
    except ImportError:
        print("Warning: openpyxl not installed. Falling back to CSV format.")
        excel_created = False
        
        # Write CSV reports as fallback
        metadata_csv_file = os.path.join(output_dir, f"metadata_duplicates_{timestamp}.csv")
        location_csv_file = os.path.join(output_dir, f"location_duplicates_{timestamp}.csv")
        
        import csv
        with open(metadata_csv_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerows(metadata_csv_rows)
        
        with open(location_csv_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerows(location_csv_rows)
    
    # Generate summary report
    summary_file = os.path.join(output_dir, f"summary_{timestamp}.txt")
    with open(summary_file, 'w') as f:
        f.write("Apple Music Library Duplicate Analysis\n")
        f.write("====================================\n\n")
        f.write(f"Analysis performed at: {datetime.datetime.now().isoformat()}\n\n")
        
        f.write("Duplicate Tracks with Different Locations\n")
        f.write("---------------------------------------\n")
        f.write(f"Found {len(metadata_duplicates)} groups of tracks with identical metadata but different locations.\n")
        f.write(f"Detailed reports: \n")
        f.write(f"  - JSON: {os.path.basename(metadata_file)}\n")
        if excel_created:
            f.write(f"  - Excel: {os.path.basename(excel_file)} (Metadata Duplicates sheet)\n")
        else:
            f.write(f"  - CSV: {os.path.basename(metadata_csv_file)}\n")
        f.write("\n")
        
        f.write("Multiple Entries with Same Location\n")
        f.write("----------------------------------\n")
        f.write(f"Found {len(location_duplicates)} instances of multiple entries pointing to the same file.\n")
        f.write(f"Detailed reports: \n")
        f.write(f"  - JSON: {os.path.basename(location_file)}\n")
        if excel_created:
            f.write(f"  - Excel: {os.path.basename(excel_file)} (Location Duplicates sheet)\n")
        else:
            f.write(f"  - CSV: {os.path.basename(location_csv_file)}\n")
    
    return metadata_file, location_file, summary_file
    
    for location, tracks in location_duplicates.items():
        # Convert any datetime objects in tracks to strings
        processed_tracks = []
        for track in tracks:
            processed_track = {}
            for k, v in track.items():
                if isinstance(v, datetime.datetime):
                    processed_track[k] = v.strftime("%Y-%m-%d %H:%M:%S")
                else:
                    processed_track[k] = v
            processed_tracks.append(processed_track)
            
        location_report['duplicate_groups'].append({
            'location': location,
            'tracks': processed_tracks
        })
    
    # Write reports to files
    metadata_file = os.path.join(output_dir, f"metadata_duplicates_{timestamp}.json")
    location_file = os.path.join(output_dir, f"location_duplicates_{timestamp}.json")
    
    with open(metadata_file, 'w') as f:
        json.dump(metadata_report, f, indent=2)
    
    with open(location_file, 'w') as f:
        json.dump(location_report, f, indent=2)
    
    # Generate summary report
    summary_file = os.path.join(output_dir, f"summary_{timestamp}.txt")
    with open(summary_file, 'w') as f:
        f.write("Apple Music Library Duplicate Analysis\n")
        f.write("====================================\n\n")
        f.write(f"Analysis performed at: {datetime.datetime.now().isoformat()}\n\n")
        
        f.write("Duplicate Tracks with Different Locations\n")
        f.write("---------------------------------------\n")
        f.write(f"Found {len(metadata_duplicates)} groups of tracks with identical metadata but different locations.\n")
        f.write(f"Detailed report: {os.path.basename(metadata_file)}\n\n")
        
        f.write("Multiple Entries with Same Location\n")
        f.write("----------------------------------\n")
        f.write(f"Found {len(location_duplicates)} instances of multiple entries pointing to the same file.\n")
        f.write(f"Detailed report: {os.path.basename(location_file)}\n")
    
    return metadata_file, location_file, summary_file

def main():
    """Main function to run the analysis."""
    args = parse_arguments()
    
    # Ensure output directory exists
    ensure_directory_exists(args.output)
    
    # Load and parse the library
    library = load_library(args.input)
    tracks = extract_tracks(library)
    
    print(f"Analyzing {len(tracks)} tracks...")
    
    # Find duplicates
    metadata_duplicates = find_duplicates_by_metadata(tracks)
    location_duplicates = find_duplicates_by_location(tracks)
    
    # Generate reports
    metadata_file, location_file, summary_file = generate_report(
        metadata_duplicates, location_duplicates, args.output
    )
    
    # Get the timestamp for the Excel file
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    excel_file = os.path.join(args.output, f"duplicates_{timestamp}.xlsx")
    
    # Print summary
    print("\nAnalysis complete!")
    print(f"Found {len(metadata_duplicates)} groups of tracks with identical metadata but different locations.")
    print(f"Found {len(location_duplicates)} instances of multiple entries pointing to the same file.")
    print(f"\nReports saved to:")
    print(f"  - {summary_file}")
    print(f"  - {metadata_file}")
    print(f"  - {location_file}")
    print(f"  - {excel_file}")
    print("\nTip: Open the Excel file to view all duplicates in a single workbook with multiple sheets.")

if __name__ == "__main__":
    main()
