# Apple Music Duplicate Finder

A Python tool that analyzes Apple Music Library.XML exports to identify and manage duplicate tracks.

## Overview

This utility helps you clean up your Apple Music library by finding duplicate entries through analysis of exported Library.XML files.

## Features

- Find tracks with identical metadata stored in different locations
- Detect multiple library entries pointing to the same file
- Generate reports of duplicate tracks for easy management

## Usage

1. **Export Your Apple Music Library**
   - Open Apple Music
   - Go to File > Library > Export Library
   - Save as `Library.XML` in the project's `/data` directory

2. **Run the Analysis**
   ```
   python analyze_library.py
   ```

3. **Review Results**
   - Check the generated report in the `/output` directory

## Requirements

- Python 3.6+
- Apple Music Library.XML export file

## Installation

```
git clone https://github.com/yourusername/apple-music-duplicate-finder.git
cd apple-music-duplicate-finder
pip install -r requirements.txt
```
