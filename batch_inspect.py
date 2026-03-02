#!/usr/bin/env python3
"""
Batch DICOM Tag Inspector

Iterates through subdirectories in the output folder, runs inspect_dicom.py
on the first DICOM file found in each directory, and saves the output to
output/dicom_tags/.
"""

import sys
from pathlib import Path
from io import StringIO

from inspect_dicom import inspect_dicom


def find_first_dicom(directory: Path) -> Path | None:
    """Find the first DICOM file in a directory (recursively)."""
    dcm_files = sorted(directory.rglob("*.dcm"))
    return dcm_files[0] if dcm_files else None


def batch_inspect(output_dir: Path, tags_dir: Path):
    """Inspect the first DICOM file in each subdirectory of output_dir."""
    # Create tags output directory if it doesn't exist
    tags_dir.mkdir(parents=True, exist_ok=True)
    
    # Get all subdirectories in output_dir (excluding hidden dirs and dicom_tags itself)
    subdirs = sorted([
        d for d in output_dir.iterdir()
        if d.is_dir() and not d.name.startswith('.') and d.name != 'dicom_tags'
    ])
    
    if not subdirs:
        print(f"No subdirectories found in {output_dir}")
        return
    
    print(f"Found {len(subdirs)} directories to process")
    print(f"Output will be saved to: {tags_dir}\n")
    
    for subdir in subdirs:
        print(f"Processing: {subdir.name}")
        
        # Find first DICOM file
        dicom_file = find_first_dicom(subdir)
        
        if dicom_file is None:
            print(f"  No DICOM files found in {subdir.name}, skipping")
            continue
        
        print(f"  Found: {dicom_file.relative_to(subdir)}")
        
        # Capture the output of inspect_dicom
        output_file = tags_dir / f"{subdir.name}_tags.txt"
        
        # Redirect stdout to capture the output
        old_stdout = sys.stdout
        sys.stdout = StringIO()
        
        try:
            inspect_dicom(dicom_file, show_private=True)
            output_content = sys.stdout.getvalue()
        finally:
            sys.stdout = old_stdout
        
        # Write to file
        output_file.write_text(output_content)
        print(f"  Saved to: {output_file.name}")
    
    print(f"\nDone! Processed {len(subdirs)} directories.")


def main():
    # Default paths relative to this script
    script_dir = Path(__file__).parent
    output_dir = Path("/Users/michael/Box Sync/Michael Gensheimer's Files/research/lesion ident segment/data/lung/nsclc_immuno_cts/dicom_anonymized") #script_dir / "output"
    tags_dir = output_dir / "dicom_tags"
    
    if not output_dir.exists():
        print(f"Error: Output directory does not exist: {output_dir}")
        sys.exit(1)
    
    batch_inspect(output_dir, tags_dir)


if __name__ == "__main__":
    main()
