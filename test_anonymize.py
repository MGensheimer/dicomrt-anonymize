#!/usr/bin/env python3
"""
Tests for DICOM RT Anonymizer, focusing on Table E1-1 recursive tag deletion.
"""

import pytest
import pydicom
from pydicom.dataset import Dataset
from pydicom.sequence import Sequence
from pydicom.tag import Tag, BaseTag

from anonymize import DICOMAnonymizer


# Tags that are NOT in Table E1-1, safe to use for test sequences
# ROIContourSequence (3006,0080) - used in RT Structure Sets, not in E1-1
NON_E1_1_SEQUENCE_TAG = Tag(0x3006, 0x0080)


class TestTableE1_1TagLoading:
    """Tests for loading Table E1-1 tags from CSV."""
    
    def test_load_table_e1_1_tags_returns_set(self):
        """Should return a set of Tag objects."""
        tags = DICOMAnonymizer.load_table_e1_1_tags()
        assert isinstance(tags, set)
        assert len(tags) > 0
        # Check that all items are BaseTag instances (Tag's parent class)
        for t in tags:
            assert isinstance(t, BaseTag)
    
    def test_load_table_e1_1_tags_contains_known_tags(self):
        """Should contain known Table E1-1 tags like AccessionNumber (0008,0050)."""
        tags = DICOMAnonymizer.load_table_e1_1_tags()
        # AccessionNumber is (0008,0050) - a well-known E1-1 tag
        assert Tag(0x0008, 0x0050) in tags
    
    def test_get_handled_tag_keywords(self):
        """Should return all keywords from the various tag lists."""
        handled = DICOMAnonymizer.get_handled_tag_keywords()
        assert 'PatientName' in handled
        assert 'PatientID' in handled
        assert 'StudyDate' in handled
        assert 'SOPInstanceUID' in handled
        assert 'InstitutionName' in handled


class TestRecursiveTagDeletion:
    """Tests for recursive Table E1-1 tag deletion."""
    
    @pytest.fixture
    def anonymizer(self):
        """Create an anonymizer instance for testing."""
        return DICOMAnonymizer()
    
    @pytest.fixture
    def simple_dataset(self):
        """Create a simple dataset with some Table E1-1 tags."""
        ds = Dataset()
        ds.PatientName = "Test^Patient"
        ds.PatientID = "12345"
        ds.Modality = "CT"  # Not in E1-1, should be preserved
        # AccessionNumber (0008,0050) is in Table E1-1
        ds.AccessionNumber = "ACC123"
        return ds
    
    def test_deletes_table_e1_1_tag_at_top_level(self, anonymizer, simple_dataset):
        """Should delete Table E1-1 tags at the top level."""
        # AccessionNumber is in Table E1-1 but also in OTHER_ID_TAGS,
        # so let's use a different tag that's only in E1-1
        # AcquisitionContextSequence (0040,0555) is in E1-1
        simple_dataset.add_new(Tag(0x0040, 0x0555), 'SQ', Sequence([]))
        
        # Verify tag exists before
        assert Tag(0x0040, 0x0555) in simple_dataset
        
        anonymizer._delete_table_e1_1_tags_recursive(simple_dataset)
        
        # Tag should be deleted
        assert Tag(0x0040, 0x0555) not in simple_dataset
    
    def test_preserves_non_e1_1_tags(self, anonymizer, simple_dataset):
        """Should preserve tags that are not in Table E1-1."""
        anonymizer._delete_table_e1_1_tags_recursive(simple_dataset)
        
        # Modality is not in E1-1, should be preserved
        assert hasattr(simple_dataset, 'Modality')
        assert simple_dataset.Modality == "CT"
    
    def test_preserves_handled_tags(self, anonymizer, simple_dataset):
        """Should preserve tags that are already handled by existing code."""
        # PatientName and PatientID are in handled_keywords
        anonymizer._delete_table_e1_1_tags_recursive(simple_dataset)
        
        # These should still exist (they're handled separately, not deleted here)
        assert hasattr(simple_dataset, 'PatientName')
        assert hasattr(simple_dataset, 'PatientID')
    
    def test_deletes_tags_in_nested_sequence(self, anonymizer):
        """Should recursively delete Table E1-1 tags inside sequences."""
        ds = Dataset()
        ds.PatientName = "Test^Patient"
        ds.Modality = "CT"
        
        # Create a sequence with a nested item containing an E1-1 tag
        seq_item = Dataset()
        seq_item.add_new(Tag(0x0040, 0x0555), 'SQ', Sequence([]))  # AcquisitionContextSequence - in E1-1
        seq_item.Modality = "MR"  # Not in E1-1
        
        # Use ROIContourSequence (3006,0080) which is NOT in Table E1-1
        ds.add_new(NON_E1_1_SEQUENCE_TAG, 'SQ', Sequence([seq_item]))
        
        # Verify nested tag exists before
        assert Tag(0x0040, 0x0555) in ds[NON_E1_1_SEQUENCE_TAG].value[0]
        
        anonymizer._delete_table_e1_1_tags_recursive(ds)
        
        # Nested E1-1 tag should be deleted
        assert Tag(0x0040, 0x0555) not in ds[NON_E1_1_SEQUENCE_TAG].value[0]
        # Non-E1-1 tag should be preserved
        assert ds[NON_E1_1_SEQUENCE_TAG].value[0].Modality == "MR"
    
    def test_deletes_tags_in_deeply_nested_sequence(self, anonymizer):
        """Should delete Table E1-1 tags in deeply nested sequences."""
        ds = Dataset()
        ds.Modality = "CT"
        
        # Use tags that are NOT in Table E1-1 for the sequence structure
        # ROIContourSequence (3006,0080), ContourSequence (3006,0040), ContourImageSequence (3006,0016)
        # These are RT Structure Set tags not in E1-1
        
        # Create deeply nested structure: ds -> seq1 -> seq2 -> seq3 -> E1-1 tag
        level3_item = Dataset()
        level3_item.add_new(Tag(0x0040, 0x0555), 'SQ', Sequence([]))  # E1-1 tag to be deleted
        level3_item.ImageType = "ORIGINAL"  # Not E1-1, should be preserved
        
        level2_item = Dataset()
        level2_item.add_new(Tag(0x3006, 0x0016), 'SQ', Sequence([level3_item]))  # ContourImageSequence
        
        level1_item = Dataset()
        level1_item.add_new(Tag(0x3006, 0x0040), 'SQ', Sequence([level2_item]))  # ContourSequence
        
        ds.add_new(Tag(0x3006, 0x0080), 'SQ', Sequence([level1_item]))  # ROIContourSequence
        
        # Verify deeply nested tag exists
        nested_item = ds[Tag(0x3006, 0x0080)].value[0][Tag(0x3006, 0x0040)].value[0][Tag(0x3006, 0x0016)].value[0]
        assert Tag(0x0040, 0x0555) in nested_item
        
        anonymizer._delete_table_e1_1_tags_recursive(ds)
        
        # Deeply nested E1-1 tag should be deleted
        nested_item = ds[Tag(0x3006, 0x0080)].value[0][Tag(0x3006, 0x0040)].value[0][Tag(0x3006, 0x0016)].value[0]
        assert Tag(0x0040, 0x0555) not in nested_item
        # Non-E1-1 tag should be preserved
        assert nested_item.ImageType == "ORIGINAL"
    
    def test_handles_empty_sequence(self, anonymizer):
        """Should handle empty sequences without error."""
        ds = Dataset()
        ds.Modality = "CT"
        # Use ROIContourSequence which is NOT in E1-1
        ds.add_new(NON_E1_1_SEQUENCE_TAG, 'SQ', Sequence([]))  # Empty sequence
        
        # Should not raise
        deleted = anonymizer._delete_table_e1_1_tags_recursive(ds)
        assert deleted == 0
        # Sequence should still exist
        assert NON_E1_1_SEQUENCE_TAG in ds
    
    def test_handles_multiple_sequence_items(self, anonymizer):
        """Should process all items in a sequence."""
        ds = Dataset()
        
        # Create sequence with multiple items, each with E1-1 tag
        items = []
        for i in range(3):
            item = Dataset()
            item.add_new(Tag(0x0040, 0x0555), 'SQ', Sequence([]))  # E1-1 tag
            item.ImageType = f"TYPE{i}"
            items.append(item)
        
        # Use ROIContourSequence which is NOT in E1-1
        ds.add_new(NON_E1_1_SEQUENCE_TAG, 'SQ', Sequence(items))
        
        # Verify all items have the E1-1 tag
        for item in ds[NON_E1_1_SEQUENCE_TAG].value:
            assert Tag(0x0040, 0x0555) in item
        
        deleted = anonymizer._delete_table_e1_1_tags_recursive(ds)
        
        # All E1-1 tags should be deleted
        assert deleted == 3
        for i, item in enumerate(ds[NON_E1_1_SEQUENCE_TAG].value):
            assert Tag(0x0040, 0x0555) not in item
            assert item.ImageType == f"TYPE{i}"
    
    def test_returns_correct_deletion_count(self, anonymizer):
        """Should return the correct count of deleted tags."""
        ds = Dataset()
        
        # Add multiple E1-1 tags at different levels
        ds.add_new(Tag(0x0040, 0x0555), 'SQ', Sequence([]))  # Top level
        
        nested_item = Dataset()
        nested_item.add_new(Tag(0x0040, 0x0556), 'ST', "test")  # AcquisitionContextDescription
        
        ds.ReferencedStudySequence = Sequence([nested_item])
        
        deleted = anonymizer._delete_table_e1_1_tags_recursive(ds)
        
        assert deleted == 2
    
    def test_preserves_rt_structure_names(self, anonymizer):
        """Should preserve RT Structure Set names even though they're in Table E1-1.
        
        These tags are in E1-1 because they *could* contain patient info, but in
        practice they contain standardized anatomical names essential for treatment.
        """
        ds = Dataset()
        ds.Modality = "RTSTRUCT"
        
        # Add StructureSetLabel (3006,0002) and StructureSetName (3006,0004)
        # These are at the top level of RT Structure Set files
        ds.add_new(Tag(0x3006, 0x0002), 'SH', "RT Structure Set")  # StructureSetLabel
        ds.add_new(Tag(0x3006, 0x0004), 'LO', "Planning Structures")  # StructureSetName
        
        # Create StructureSetROISequence with ROI names
        roi1 = Dataset()
        roi1.ROINumber = 1
        roi1.add_new(Tag(0x3006, 0x0026), 'LO', "PTV")  # ROIName
        
        roi2 = Dataset()
        roi2.ROINumber = 2
        roi2.add_new(Tag(0x3006, 0x0026), 'LO', "Heart")  # ROIName
        
        roi3 = Dataset()
        roi3.ROINumber = 3
        roi3.add_new(Tag(0x3006, 0x0026), 'LO', "Lung_L")  # ROIName
        
        ds.StructureSetROISequence = Sequence([roi1, roi2, roi3])
        
        # Create RTROIObservationsSequence with observation labels
        obs1 = Dataset()
        obs1.ObservationNumber = 1
        obs1.add_new(Tag(0x3006, 0x0085), 'SH', "PTV_Label")  # ROIObservationLabel
        
        ds.RTROIObservationsSequence = Sequence([obs1])
        
        # Run the deletion
        anonymizer._delete_table_e1_1_tags_recursive(ds)
        
        # All structure-related tags should be preserved
        assert Tag(0x3006, 0x0002) in ds  # StructureSetLabel
        assert ds[Tag(0x3006, 0x0002)].value == "RT Structure Set"
        
        assert Tag(0x3006, 0x0004) in ds  # StructureSetName
        assert ds[Tag(0x3006, 0x0004)].value == "Planning Structures"
        
        # ROI names should be preserved
        for i, expected_name in enumerate(["PTV", "Heart", "Lung_L"]):
            assert Tag(0x3006, 0x0026) in ds.StructureSetROISequence[i]
            assert ds.StructureSetROISequence[i][Tag(0x3006, 0x0026)].value == expected_name
        
        # ROI observation labels should be preserved
        assert Tag(0x3006, 0x0085) in ds.RTROIObservationsSequence[0]
        assert ds.RTROIObservationsSequence[0][Tag(0x3006, 0x0085)].value == "PTV_Label"


class TestFullAnonymization:
    """Integration tests for the full anonymization including Table E1-1."""
    
    @pytest.fixture
    def anonymizer(self):
        return DICOMAnonymizer()
    
    def test_anonymize_dataset_deletes_e1_1_tags(self, anonymizer):
        """Full anonymize_dataset should delete Table E1-1 tags."""
        ds = Dataset()
        ds.PatientName = "Test^Patient"
        ds.PatientID = "12345"
        ds.Modality = "CT"
        ds.SOPClassUID = "1.2.840.10008.5.1.4.1.1.2"
        ds.SOPInstanceUID = "1.2.3.4.5.6.7.8.9"
        # Add E1-1 only tag
        ds.add_new(Tag(0x0040, 0x0555), 'SQ', Sequence([]))
        
        anonymizer.anonymize_dataset(ds)
        
        # E1-1 tag should be gone
        assert Tag(0x0040, 0x0555) not in ds
        # Patient info should be anonymized (not deleted)
        assert ds.PatientName == "ANONYMOUS"
        assert ds.PatientID == "000000"
        # Modality should be preserved
        assert ds.Modality == "CT"
    
    def test_anonymize_preserves_uid_handling(self, anonymizer):
        """UIDs should be remapped, not deleted, even if in Table E1-1."""
        ds = Dataset()
        ds.PatientName = "Test^Patient"
        ds.PatientID = "12345"
        ds.SOPClassUID = "1.2.840.10008.5.1.4.1.1.2"
        original_sop_uid = "1.2.3.4.5.6.7.8.9"
        ds.SOPInstanceUID = original_sop_uid
        ds.StudyInstanceUID = "1.2.3.4.5.6.7.8.10"
        ds.SeriesInstanceUID = "1.2.3.4.5.6.7.8.11"
        
        anonymizer.anonymize_dataset(ds)
        
        # UIDs should exist but be different (remapped)
        assert hasattr(ds, 'SOPInstanceUID')
        assert ds.SOPInstanceUID != original_sop_uid
        assert hasattr(ds, 'StudyInstanceUID')
        assert hasattr(ds, 'SeriesInstanceUID')

    def test_updates_file_meta_media_storage_sop_instance_uid(self, anonymizer):
        """file_meta MediaStorageSOPInstanceUID should match remapped SOPInstanceUID."""
        ds = Dataset()
        ds.file_meta = Dataset()
        ds.SOPClassUID = "1.2.840.10008.5.1.4.1.1.2"
        original_uid = "1.2.3.4.5.6.7.8.9"
        ds.SOPInstanceUID = original_uid
        ds.file_meta.MediaStorageSOPInstanceUID = original_uid

        anonymizer.anonymize_dataset(ds)

        assert ds.SOPInstanceUID != original_uid
        assert ds.file_meta.MediaStorageSOPInstanceUID == ds.SOPInstanceUID


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
