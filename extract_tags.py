#!/usr/bin/env python3
"""
Extract DICOM tags from table_e1_1.txt and save to CSV.
Tags are in the format: (abcd,efgh)
"""

import re
import csv


def extract_dicom_tags(input_file: str, output_file: str) -> None:
    """
    Extract DICOM tags from input file and save to CSV.
    
    Args:
        input_file: Path to input text file containing DICOM tags
        output_file: Path to output CSV file
    """
    # Pattern to match DICOM tags in format (XXXX,XXXX)
    # where X is a hexadecimal digit
    tag_pattern = re.compile(r'\(([0-9a-fA-F]{4}),([0-9a-fA-F]{4})\)')
    
    tags = []
    
    with open(input_file, 'r') as f:
        for line in f:
            match = tag_pattern.search(line)
            if match:
                group = match.group(1).upper()
                element = match.group(2).upper()
                tags.append((group, element))
    
    # Write to CSV
    with open(output_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['group', 'element'])
        writer.writerows(tags)
    
    print(f"Extracted {len(tags)} DICOM tags to {output_file}")


if __name__ == '__main__':
    extract_dicom_tags('table_e1_1.txt', 'table_e1_1_tags.csv')
