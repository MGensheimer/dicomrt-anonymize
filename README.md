# DICOM RT Anonymizer

A Python tool for anonymizing DICOM radiotherapy files, including CT images and RT Structure Sets, while maintaining UID relationships between referenced files.

by Michael Gensheimer, Claude, and OpenAI Codex

## Features

- **Comprehensive anonymization** based on DICOM Table E.1-1 (Application Level Confidentiality Profile Attributes)
- **UID relationship preservation** - remaps all UIDs consistently so RT Structure Sets still reference their CT images correctly
- **RT Structure name preservation** - keeps anatomical structure names (e.g., "PTV", "Heart", "Lung_L") that are essential for treatment planning
- **Private tag removal** - removes vendor-specific tags that may contain identifying information
- **Recursive anonymization** - handles deeply nested DICOM sequences

## Installation

```bash
# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Usage

### Anonymize DICOM Files

```bash
python anonymize.py \
    --ct-dir ./data/ct_slices \
    --rtstruct-dir ./data/rt_structure_set \
    --output-dir ./output
```

#### Options

| Option | Description |
|--------|-------------|
| `-c, --ct-dir` | Directory containing CT slice DICOM files (required) |
| `-r, --rtstruct-dir` | Directory containing RT Structure Set DICOM files (required) |
| `-o, --output-dir` | Output directory for anonymized files (required) |
| `--patient-name` | Anonymized patient name (default: `ANONYMOUS`) |
| `--patient-id` | Anonymized patient ID (default: `000000`) |
| `--save-uid-mapping` | Save UID mapping to file (WARNING: this file is not anonymized since it has the original UIDs) |

### Utility Scripts

#### Inspect DICOM Files

View all DICOM tags in a file for verification:

```bash
python inspect_dicom.py path/to/file.dcm
```

## What Gets Anonymized

The anonymizer handles the following categories of data:

### Replaced with Anonymous Values
- Patient name, ID, birth date, sex, age, address
- Study/series dates and times
- Institution name and address
- Physician names
- Study/series descriptions

### Remapped (New UIDs Generated)
- SOP Instance UID
- Study Instance UID
- Series Instance UID
- Frame of Reference UID
- All referenced UIDs in RT Structure Sets

### Deleted
- All tags from DICOM Table E1-1 not handled above
- Private (vendor-specific) tags

### Preserved
- RT Structure names (ROIName, StructureSetLabel, etc.). Careful, these could contain patient name, etc.!
- Modality and other technical metadata
- Contour data and geometric information

## Notes

- I recommend using the [Weasis DICOM viewer](https://weasis.org/) to verify that the output files include the structures; it does a better job than other viewers of processing RT structure set files.
- I have not tested the software on all scanners and kinds of DICOM files, so anonymization is not guaranteed. Always check the output files' DICOM tags to make sure there is no patient information left.

## Testing

```bash
pytest test_anonymize.py -v
```

## License

MIT
