#!/usr/bin/env python3
"""
DICOM RT Anonymizer

Anonymizes DICOM files including CT images and RT Structure Sets,
maintaining UID relationships between referenced files.
"""

import argparse
import json
from pathlib import Path

import pydicom
from pydicom.uid import generate_uid


class DICOMAnonymizer:
    """Anonymizes DICOM files while maintaining UID relationships."""
    
    # DICOM tags that contain UIDs which may need remapping
    UID_TAGS = [
        'SOPInstanceUID',
        'StudyInstanceUID', 
        'SeriesInstanceUID',
        'FrameOfReferenceUID',
        'ReferencedSOPInstanceUID',
        'ReferencedFrameOfReferenceUID',
    ]
    
    # Tags containing dates to anonymize
    DATE_TAGS = [
        'StudyDate',
        'SeriesDate', 
        'AcquisitionDate',
        'ContentDate',
        'InstanceCreationDate',
        'PatientBirthDate',
        'StructureSetDate',
    ]
    
    # Tags containing times to anonymize
    TIME_TAGS = [
        'StudyTime',
        'SeriesTime',
        'AcquisitionTime', 
        'ContentTime',
        'InstanceCreationTime',
        'StructureSetTime',
    ]
    
    # Tags containing patient identifiers
    PATIENT_TAGS = [
        'PatientName',
        'PatientID',
        'PatientBirthDate',
        'PatientSex',
        'PatientAge',
        'PatientAddress',
        'PatientTelephoneNumbers',
        'OtherPatientIDs',
        'OtherPatientNames',
    ]
    
    # Other potentially identifying tags
    OTHER_ID_TAGS = [
        'InstitutionName',
        'InstitutionAddress',
        'InstitutionalDepartmentName',
        'ReferringPhysicianName',
        'PhysiciansOfRecord',
        'PerformingPhysicianName',
        'OperatorsName',
        'StationName',
        'StudyDescription',
        'SeriesDescription',
        'AccessionNumber',
        'PatientComments',
        'InsurancePlanIdentification',
        'ProtocolName',
        'CommentsOnThePerformedProcedureStep',
    ]
    
    def __init__(self, anon_patient_name: str = "ANONYMOUS", anon_patient_id: str = "000000"):
        """
        Initialize the anonymizer.
        
        Args:
            anon_patient_name: Replacement patient name
            anon_patient_id: Replacement patient ID
        """
        self.uid_map: dict[str, str] = {}  # Maps original UIDs to new UIDs
        self.anon_patient_name = anon_patient_name
        self.anon_patient_id = anon_patient_id
        self.anon_date = "19000101"  # Default anonymized date
        self.anon_time = "000000"    # Default anonymized time
        
    def get_or_create_uid(self, original_uid: str) -> str:
        """
        Get the mapped UID for an original UID, creating a new one if needed.
        
        Args:
            original_uid: The original DICOM UID
            
        Returns:
            The new anonymized UID (consistent for the same original)
        """
        if not original_uid:
            return original_uid
            
        original_uid = str(original_uid)
        
        if original_uid not in self.uid_map:
            self.uid_map[original_uid] = generate_uid()
            
        return self.uid_map[original_uid]
    
    def anonymize_dataset(self, ds: pydicom.Dataset) -> pydicom.Dataset:
        """
        Anonymize a DICOM dataset in place.
        
        Args:
            ds: The pydicom Dataset to anonymize
            
        Returns:
            The anonymized dataset
        """
        # Anonymize core UIDs
        for tag in self.UID_TAGS:
            if hasattr(ds, tag):
                original = getattr(ds, tag)
                setattr(ds, tag, self.get_or_create_uid(original))
        
        # Anonymize dates
        for tag in self.DATE_TAGS:
            if hasattr(ds, tag):
                setattr(ds, tag, self.anon_date)
        
        # Anonymize times
        for tag in self.TIME_TAGS:
            if hasattr(ds, tag):
                setattr(ds, tag, self.anon_time)
        
        # Anonymize patient info
        if hasattr(ds, 'PatientName'):
            ds.PatientName = self.anon_patient_name
        if hasattr(ds, 'PatientID'):
            ds.PatientID = self.anon_patient_id
        if hasattr(ds, 'PatientBirthDate'):
            ds.PatientBirthDate = ""
        if hasattr(ds, 'PatientSex'):
            ds.PatientSex = ""
        if hasattr(ds, 'PatientAge'):
            ds.PatientAge = ""
            
        # Clear other identifying info
        for tag in self.OTHER_ID_TAGS:
            if hasattr(ds, tag):
                setattr(ds, tag, "")
        
        # Handle RT Structure Set specific sequences
        if hasattr(ds, 'ReferencedFrameOfReferenceSequence'):
            self._anonymize_referenced_frame_of_reference_sequence(
                ds.ReferencedFrameOfReferenceSequence
            )
        
        # Handle ROI Contour Sequence (contains image references per contour)
        if hasattr(ds, 'ROIContourSequence'):
            self._anonymize_roi_contour_sequence(ds.ROIContourSequence)
        
        # Remove private tags (vendor-specific data that may contain identifying info)
        # See: https://pydicom.github.io/pydicom/stable/auto_examples/metadata_processing/plot_anonymize.html
        ds.remove_private_tags()
            
        return ds
    
    def _anonymize_referenced_frame_of_reference_sequence(self, seq):
        """Anonymize UIDs in ReferencedFrameOfReferenceSequence."""
        for frame_ref in seq:
            if hasattr(frame_ref, 'FrameOfReferenceUID'):
                frame_ref.FrameOfReferenceUID = self.get_or_create_uid(
                    frame_ref.FrameOfReferenceUID
                )
            
            if hasattr(frame_ref, 'RTReferencedStudySequence'):
                for study_ref in frame_ref.RTReferencedStudySequence:
                    if hasattr(study_ref, 'ReferencedSOPInstanceUID'):
                        study_ref.ReferencedSOPInstanceUID = self.get_or_create_uid(
                            study_ref.ReferencedSOPInstanceUID
                        )
                    if hasattr(study_ref, 'ReferencedSOPClassUID'):
                        # SOP Class UIDs are standard and should NOT be changed
                        pass
                    
                    if hasattr(study_ref, 'RTReferencedSeriesSequence'):
                        for series_ref in study_ref.RTReferencedSeriesSequence:
                            if hasattr(series_ref, 'SeriesInstanceUID'):
                                series_ref.SeriesInstanceUID = self.get_or_create_uid(
                                    series_ref.SeriesInstanceUID
                                )
                            
                            if hasattr(series_ref, 'ContourImageSequence'):
                                for img_ref in series_ref.ContourImageSequence:
                                    if hasattr(img_ref, 'ReferencedSOPInstanceUID'):
                                        img_ref.ReferencedSOPInstanceUID = self.get_or_create_uid(
                                            img_ref.ReferencedSOPInstanceUID
                                        )
    
    def _anonymize_roi_contour_sequence(self, seq):
        """Anonymize UIDs in ROIContourSequence."""
        for roi_contour in seq:
            if hasattr(roi_contour, 'ContourSequence'):
                for contour in roi_contour.ContourSequence:
                    if hasattr(contour, 'ContourImageSequence'):
                        for img_ref in contour.ContourImageSequence:
                            if hasattr(img_ref, 'ReferencedSOPInstanceUID'):
                                img_ref.ReferencedSOPInstanceUID = self.get_or_create_uid(
                                    img_ref.ReferencedSOPInstanceUID
                                )
    
    def save_uid_mapping(self, filepath: Path):
        """Save the UID mapping to a JSON file for reference."""
        with open(filepath, 'w') as f:
            json.dump(self.uid_map, f, indent=2)
        print(f"UID mapping saved to: {filepath}")


def anonymize_dicom_directory(
    ct_dir: Path,
    rtstruct_dir: Path, 
    output_dir: Path,
    anon_patient_name: str = "ANONYMOUS",
    anon_patient_id: str = "000000",
    save_uid_mapping: bool = False
):
    """
    Anonymize a directory of DICOM files.
    
    Args:
        ct_dir: Directory containing CT slice DICOM files
        rtstruct_dir: Directory containing RT Structure Set files
        output_dir: Directory to write anonymized files
        anon_patient_name: Replacement patient name
        anon_patient_id: Replacement patient ID
        save_uid_mapping: If True, save UID mapping to file (breaks anonymization)
    """
    anonymizer = DICOMAnonymizer(anon_patient_name, anon_patient_id)
    
    # Create output subdirectories
    ct_output = output_dir / "ct_slices"
    rtstruct_output = output_dir / "rt_structure_set"
    ct_output.mkdir(parents=True, exist_ok=True)
    rtstruct_output.mkdir(parents=True, exist_ok=True)
    
    # First pass: Process CT slices (to build UID mapping)
    print(f"\n{'='*60}")
    print("DICOM RT Anonymizer")
    print(f"{'='*60}")
    print(f"\nProcessing CT slices from: {ct_dir}")
    
    ct_files = sorted(ct_dir.glob("*.dcm"))
    print(f"Found {len(ct_files)} CT slice files")
    
    for i, ct_file in enumerate(ct_files, 1):
        ds = pydicom.dcmread(ct_file)
        
        # Store original patient info for logging (first file only)
        if i == 1:
            orig_name = str(ds.PatientName) if hasattr(ds, 'PatientName') else 'N/A'
            orig_id = str(ds.PatientID) if hasattr(ds, 'PatientID') else 'N/A'
            print(f"\nOriginal Patient Name: {orig_name}")
            print(f"Original Patient ID: {orig_id}")
            print(f"\nAnonymizing to:")
            print(f"  Patient Name: {anon_patient_name}")
            print(f"  Patient ID: {anon_patient_id}")
            print()
        
        # Anonymize
        anonymizer.anonymize_dataset(ds)
        
        # Save with anonymized filename (ct_slice_001.dcm, ct_slice_002.dcm, etc.)
        anon_filename = f"ct_slice_{i:03d}.dcm"
        output_path = ct_output / anon_filename
        ds.save_as(output_path)
        
        if i % 50 == 0 or i == len(ct_files):
            print(f"  Processed {i}/{len(ct_files)} CT slices...")
    
    print(f"\n✓ CT slices anonymized and saved to: {ct_output}")
    
    # Second pass: Process RT Structure Sets
    print(f"\nProcessing RT Structure Sets from: {rtstruct_dir}")
    
    rtstruct_files = list(rtstruct_dir.glob("*.dcm"))
    print(f"Found {len(rtstruct_files)} RT Structure Set files")
    
    for i, rtstruct_file in enumerate(rtstruct_files, 1):
        ds = pydicom.dcmread(rtstruct_file)
        
        # Anonymize (UID mapping already exists from CT processing)
        anonymizer.anonymize_dataset(ds)
        
        # Save with anonymized filename
        if len(rtstruct_files) == 1:
            anon_filename = "rt_structure_set.dcm"
        else:
            anon_filename = f"rt_structure_set_{i}.dcm"
        output_path = rtstruct_output / anon_filename
        ds.save_as(output_path)
        print(f"  Processed: {rtstruct_file.name} -> {anon_filename}")
    
    print(f"\n✓ RT Structure Sets anonymized and saved to: {rtstruct_output}")
    
    # Optionally save UID mapping (disabled by default to preserve anonymization)
    if save_uid_mapping:
        mapping_file = output_dir / "uid_mapping.json"
        anonymizer.save_uid_mapping(mapping_file)
    
    # Summary
    print(f"\n{'='*60}")
    print("ANONYMIZATION COMPLETE")
    print(f"{'='*60}")
    print(f"Total UIDs remapped: {len(anonymizer.uid_map)}")
    print(f"Output directory: {output_dir}")
    print(f"\nOutput contents:")
    print(f"  - {ct_output.relative_to(output_dir)}/  ({len(ct_files)} files)")
    print(f"  - {rtstruct_output.relative_to(output_dir)}/  ({len(rtstruct_files)} files)")
    if save_uid_mapping:
        print(f"  - uid_mapping.json")
    
    return anonymizer


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Anonymize DICOM RT files (CT slices and RT Structure Sets)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --ct-dir ./data/ct_slices --rtstruct-dir ./data/rt_structure_set --output-dir ./output
  %(prog)s -c /path/to/ct -r /path/to/rtstruct -o /path/to/output --patient-name "ANON" --patient-id "12345"
        """
    )
    
    parser.add_argument(
        "-c", "--ct-dir",
        type=Path,
        required=True,
        help="Directory containing CT slice DICOM files"
    )
    
    parser.add_argument(
        "-r", "--rtstruct-dir",
        type=Path,
        required=True,
        help="Directory containing RT Structure Set DICOM files"
    )
    
    parser.add_argument(
        "-o", "--output-dir",
        type=Path,
        required=True,
        help="Output directory for anonymized files"
    )
    
    parser.add_argument(
        "--patient-name",
        type=str,
        default="ANONYMOUS",
        help="Anonymized patient name (default: ANONYMOUS)"
    )
    
    parser.add_argument(
        "--patient-id",
        type=str,
        default="000000",
        help="Anonymized patient ID (default: 000000)"
    )
    
    parser.add_argument(
        "--save-uid-mapping",
        action="store_true",
        help="Save UID mapping to file (WARNING: breaks anonymization by allowing re-identification)"
    )
    
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    
    # Validate input directories exist
    if not args.ct_dir.exists():
        print(f"Error: CT directory does not exist: {args.ct_dir}")
        exit(1)
    if not args.rtstruct_dir.exists():
        print(f"Error: RT Structure Set directory does not exist: {args.rtstruct_dir}")
        exit(1)
    
    # Run anonymization
    anonymize_dicom_directory(
        ct_dir=args.ct_dir,
        rtstruct_dir=args.rtstruct_dir,
        output_dir=args.output_dir,
        anon_patient_name=args.patient_name,
        anon_patient_id=args.patient_id,
        save_uid_mapping=args.save_uid_mapping
    )
