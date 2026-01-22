#!/usr/bin/env python3
"""
DICOM RT Anonymize - UID Analysis Script

This script analyzes DICOM files to understand UID relationships,
particularly between CT images and RT Structure Sets.
"""

import pydicom
from pathlib import Path
from datetime import datetime


def get_uid_info(ds, label=""):
    """Extract common UIDs from a DICOM dataset."""
    info = {}
    
    # Core UIDs present in most DICOM files
    uid_tags = [
        ('SOPInstanceUID', 'SOP Instance UID'),
        ('SOPClassUID', 'SOP Class UID'),
        ('StudyInstanceUID', 'Study Instance UID'),
        ('SeriesInstanceUID', 'Series Instance UID'),
        ('FrameOfReferenceUID', 'Frame of Reference UID'),
    ]
    
    for attr, name in uid_tags:
        if hasattr(ds, attr):
            info[name] = str(getattr(ds, attr))
    
    return info


def get_rt_struct_references(ds):
    """Extract referenced UIDs from an RT Structure Set."""
    references = {
        'Referenced Frame of Reference UIDs': [],
        'Referenced Study UIDs': [],
        'Referenced Series UIDs': [],
        'Referenced SOP Instance UIDs': [],
    }
    
    # RT Structure Sets have a ReferencedFrameOfReferenceSequence
    if hasattr(ds, 'ReferencedFrameOfReferenceSequence'):
        for frame_ref in ds.ReferencedFrameOfReferenceSequence:
            if hasattr(frame_ref, 'FrameOfReferenceUID'):
                references['Referenced Frame of Reference UIDs'].append(
                    str(frame_ref.FrameOfReferenceUID)
                )
            
            # Each frame of reference can have RT Referenced Study Sequence
            if hasattr(frame_ref, 'RTReferencedStudySequence'):
                for study_ref in frame_ref.RTReferencedStudySequence:
                    if hasattr(study_ref, 'ReferencedSOPInstanceUID'):
                        references['Referenced Study UIDs'].append(
                            str(study_ref.ReferencedSOPInstanceUID)
                        )
                    
                    # Each study can have RT Referenced Series Sequence
                    if hasattr(study_ref, 'RTReferencedSeriesSequence'):
                        for series_ref in study_ref.RTReferencedSeriesSequence:
                            if hasattr(series_ref, 'SeriesInstanceUID'):
                                references['Referenced Series UIDs'].append(
                                    str(series_ref.SeriesInstanceUID)
                                )
                            
                            # Each series has Contour Image Sequence
                            if hasattr(series_ref, 'ContourImageSequence'):
                                for img_ref in series_ref.ContourImageSequence:
                                    if hasattr(img_ref, 'ReferencedSOPInstanceUID'):
                                        references['Referenced SOP Instance UIDs'].append(
                                            str(img_ref.ReferencedSOPInstanceUID)
                                        )
    
    # Also check ROI Contour Sequence for image references
    if hasattr(ds, 'ROIContourSequence'):
        for roi_contour in ds.ROIContourSequence:
            if hasattr(roi_contour, 'ContourSequence'):
                for contour in roi_contour.ContourSequence:
                    if hasattr(contour, 'ContourImageSequence'):
                        for img_ref in contour.ContourImageSequence:
                            if hasattr(img_ref, 'ReferencedSOPInstanceUID'):
                                uid = str(img_ref.ReferencedSOPInstanceUID)
                                if uid not in references['Referenced SOP Instance UIDs']:
                                    references['Referenced SOP Instance UIDs'].append(uid)
    
    return references


def analyze_dicom_files(data_dir: Path, log_file: Path):
    """Analyze DICOM files and write UID information to log."""
    
    lines = []
    lines.append("=" * 70)
    lines.append("DICOM UID Analysis Report")
    lines.append(f"Generated: {datetime.now().isoformat()}")
    lines.append("=" * 70)
    lines.append("")
    
    ct_uids = {}
    
    # Analyze CT slice
    ct_file = data_dir / "ct_slice.dcm"
    if ct_file.exists():
        lines.append("-" * 70)
        lines.append("CT SLICE: ct_slice.dcm")
        lines.append("-" * 70)
        
        ds = pydicom.dcmread(ct_file)
        ct_uids = get_uid_info(ds)
        
        # Add patient/study info for context
        if hasattr(ds, 'PatientName'):
            lines.append(f"Patient Name: {ds.PatientName}")
        if hasattr(ds, 'PatientID'):
            lines.append(f"Patient ID: {ds.PatientID}")
        if hasattr(ds, 'Modality'):
            lines.append(f"Modality: {ds.Modality}")
        
        lines.append("")
        lines.append("UIDs:")
        for name, uid in ct_uids.items():
            lines.append(f"  {name}: {uid}")
        lines.append("")
    
    # Analyze RT Structure Set
    rtstruct_file = data_dir / "rt_structure_set.dcm"
    if rtstruct_file.exists():
        lines.append("-" * 70)
        lines.append("RT STRUCTURE SET: rt_structure_set.dcm")
        lines.append("-" * 70)
        
        ds = pydicom.dcmread(rtstruct_file)
        rtstruct_uids = get_uid_info(ds)
        
        if hasattr(ds, 'PatientName'):
            lines.append(f"Patient Name: {ds.PatientName}")
        if hasattr(ds, 'PatientID'):
            lines.append(f"Patient ID: {ds.PatientID}")
        if hasattr(ds, 'Modality'):
            lines.append(f"Modality: {ds.Modality}")
        if hasattr(ds, 'StructureSetLabel'):
            lines.append(f"Structure Set Label: {ds.StructureSetLabel}")
        
        lines.append("")
        lines.append("UIDs:")
        for name, uid in rtstruct_uids.items():
            lines.append(f"  {name}: {uid}")
        
        lines.append("")
        lines.append("Referenced UIDs (links to other DICOM files):")
        references = get_rt_struct_references(ds)
        for ref_type, uids in references.items():
            if uids:
                lines.append(f"  {ref_type}:")
                for uid in uids:
                    lines.append(f"    - {uid}")
        
        # List structure names
        if hasattr(ds, 'StructureSetROISequence'):
            lines.append("")
            lines.append(f"ROI Structures ({len(ds.StructureSetROISequence)} total):")
            for roi in ds.StructureSetROISequence:
                lines.append(f"  - {roi.ROINumber}: {roi.ROIName}")
        
        lines.append("")
    
    # Cross-reference analysis
    lines.append("-" * 70)
    lines.append("UID CROSS-REFERENCE ANALYSIS")
    lines.append("-" * 70)
    
    if ct_uids and references:
        # Check if CT SOPInstanceUID is referenced
        ct_sop = ct_uids.get('SOP Instance UID', '')
        if ct_sop in references.get('Referenced SOP Instance UIDs', []):
            lines.append(f"✓ CT SOP Instance UID is referenced by RT Structure Set")
        else:
            lines.append(f"✗ CT SOP Instance UID NOT found in RT Structure Set references")
        
        # Check Frame of Reference match
        ct_for = ct_uids.get('Frame of Reference UID', '')
        if ct_for in references.get('Referenced Frame of Reference UIDs', []):
            lines.append(f"✓ Frame of Reference UIDs match")
        else:
            lines.append(f"✗ Frame of Reference UIDs do NOT match")
        
        # Check Series match
        ct_series = ct_uids.get('Series Instance UID', '')
        if ct_series in references.get('Referenced Series UIDs', []):
            lines.append(f"✓ Series Instance UIDs match")
        else:
            lines.append(f"✗ Series Instance UIDs do NOT match")
        
        # Check Study match
        ct_study = ct_uids.get('Study Instance UID', '')
        if ct_study in references.get('Referenced Study UIDs', []):
            lines.append(f"✓ Study Instance UIDs match")
        else:
            lines.append(f"✗ Study Instance UIDs do NOT match")
    
    lines.append("")
    lines.append("=" * 70)
    lines.append("ANONYMIZATION IMPLICATIONS")
    lines.append("=" * 70)
    lines.append("""
When anonymizing DICOM RT files, UIDs must be handled carefully:

1. Generate NEW UIDs for anonymized files (don't reuse originals)
2. Maintain UID RELATIONSHIPS - if CT gets new UIDs, RT Structure Set 
   references must be updated to point to the new CT UIDs
3. Use a UID mapping table to track old->new UID translations
4. Process files in the correct order or use two-pass approach

Key UIDs to map:
- Study Instance UID (shared across all files in a study)
- Series Instance UID (shared across files in a series)  
- SOP Instance UID (unique per file)
- Frame of Reference UID (links RT structures to image geometry)
""")
    
    # Write to log file
    log_content = "\n".join(lines)
    log_file.write_text(log_content)
    print(f"UID analysis written to: {log_file}")
    print()
    print(log_content)


if __name__ == "__main__":
    script_dir = Path(__file__).parent
    data_dir = script_dir / "data"
    log_file = script_dir / "uid_analysis.log"
    
    analyze_dicom_files(data_dir, log_file)
