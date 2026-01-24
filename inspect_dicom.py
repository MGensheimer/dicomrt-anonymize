#!/usr/bin/env python3
"""
DICOM Tag Inspector

Prints all DICOM tags in a file for verification purposes.

"""

import argparse
from pathlib import Path

import pydicom


def inspect_dicom(filepath: Path, show_private: bool = True):
    """Print all DICOM tags in a file, including nested sequences."""
    ds = pydicom.dcmread(filepath)
    
    print(f"{'='*60}")
    print(f"DICOM File: {filepath}")
    print(f"{'='*60}\n")
    
    total_elements = [0]  # Use list to allow mutation in nested function
    
    # Print file meta information first
    if hasattr(ds, 'file_meta') and ds.file_meta:
        print("--- File Meta Information ---")
        for elem in ds.file_meta:
            tag_str = f"({elem.tag.group:04X},{elem.tag.element:04X})"
            keyword = elem.keyword if elem.keyword else "Unknown"
            value = str(elem.value)
            if len(value) > 80:
                value = value[:77] + "..."
            print(f"{tag_str} {keyword}: {value}")
            total_elements[0] += 1
        print("\n--- Dataset ---")
    
    def print_element(elem, indent=0):
        """Recursively print a DICOM element."""
        prefix = "  " * indent
        
        # Skip private tags unless requested
        if elem.tag.is_private and not show_private:
            return
        
        total_elements[0] += 1
        tag_str = f"({elem.tag.group:04X},{elem.tag.element:04X})"
        keyword = elem.keyword if elem.keyword else "Unknown"
        
        if elem.VR == "SQ":
            print(f"{prefix}{tag_str} {keyword}: <Sequence with {len(elem.value)} item(s)>")
            for i, item in enumerate(elem.value):
                print(f"{prefix}  --- Item {i} ---")
                for sub_elem in item:
                    print_element(sub_elem, indent + 2)
        else:
            value = str(elem.value)
            if len(value) > 80:
                value = value[:77] + "..."
            print(f"{prefix}{tag_str} {keyword}: {value}")
    
    for elem in ds:
        print_element(elem)
    
    print(f"\n{'='*60}")
    print(f"Total elements (including nested): {total_elements[0]}")
    if not show_private:
        # Count private tags recursively
        def count_private(dataset):
            count = 0
            for elem in dataset:
                if elem.tag.is_private:
                    count += 1
                if elem.VR == "SQ":
                    for item in elem.value:
                        count += count_private(item)
            return count
        private_count = count_private(ds)
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
        "-p", "--hide-private",
        action="store_true",
        help="Hide private (vendor-specific) tags"
    )
    
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    
    if not args.file.exists():
        print(f"Error: File does not exist: {args.file}")
        exit(1)
    
    inspect_dicom(args.file, not args.hide_private)
