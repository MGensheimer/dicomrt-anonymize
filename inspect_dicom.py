#!/usr/bin/env python3
"""
DICOM Tag Inspector

Prints all DICOM tags in a file for verification purposes.

python anonymize.py -c ./data/ct_slices -r ./data/rt_structure_set -o ./output
"""

import argparse
from pathlib import Path

import pydicom


def inspect_dicom(filepath: Path, show_private: bool = False):
    """Print all DICOM tags in a file."""
    ds = pydicom.dcmread(filepath)
    
    print(f"{'='*60}")
    print(f"DICOM File: {filepath}")
    print(f"{'='*60}\n")
    
    for elem in ds:
        # Skip private tags unless requested
        if elem.tag.is_private and not show_private:
            continue
        
        # Format the output
        tag_str = f"({elem.tag.group:04X},{elem.tag.element:04X})"
        keyword = elem.keyword if elem.keyword else "Unknown"
        
        # Truncate long values for readability
        value = str(elem.value)
        if len(value) > 80:
            value = value[:77] + "..."
        
        # Handle sequences specially
        if elem.VR == "SQ":
            print(f"{tag_str} {keyword}: <Sequence with {len(elem.value)} item(s)>")
        else:
            print(f"{tag_str} {keyword}: {value}")
    
    print(f"\n{'='*60}")
    print(f"Total elements: {len(ds)}")
    if not show_private:
        private_count = sum(1 for elem in ds if elem.tag.is_private)
        if private_count > 0:
            print(f"Private tags hidden: {private_count} (use --show-private to display)")
    print(f"{'='*60}")


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Inspect DICOM file tags for verification"
    )
    
    parser.add_argument(
        "file",
        type=Path,
        help="Path to the DICOM file to inspect"
    )
    
    parser.add_argument(
        "-p", "--show-private",
        action="store_true",
        help="Show private (vendor-specific) tags"
    )
    
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    
    if not args.file.exists():
        print(f"Error: File does not exist: {args.file}")
        exit(1)
    
    inspect_dicom(args.file, args.show_private)
