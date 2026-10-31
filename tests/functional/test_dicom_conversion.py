"""Runtime compatibility regression; requires the real image-conversion dependencies."""

import nibabel as nib
import numpy as np
from pydicom import dcmwrite
from pydicom.dataset import FileDataset, FileMetaDataset
from pydicom.uid import CTImageStorage, ExplicitVRLittleEndian, generate_uid

from pumaz.image_conversion import non_nifti_to_nifti


def test_dicom_directory_standardization_preserves_pixels_and_world_geometry(tmp_path):
    source = tmp_path / "dicom"
    source.mkdir()
    output = tmp_path / "nifti"
    output.mkdir()
    study, series, frame = generate_uid(), generate_uid(), generate_uid()
    for z in range(5):
        instance = generate_uid()
        meta = FileMetaDataset()
        meta.TransferSyntaxUID = ExplicitVRLittleEndian
        meta.MediaStorageSOPClassUID = CTImageStorage
        meta.MediaStorageSOPInstanceUID = instance
        ds = FileDataset(None, {}, file_meta=meta, preamble=b"\0" * 128)
        ds.SOPClassUID, ds.SOPInstanceUID = CTImageStorage, instance
        ds.StudyInstanceUID, ds.SeriesInstanceUID = study, series
        ds.FrameOfReferenceUID = frame
        ds.PatientName, ds.PatientID = "Synthetic^Fixture", "SYNTHETIC"
        ds.Modality, ds.Manufacturer = "CT", "SYNTHETIC"
        ds.ImageType = ["ORIGINAL", "PRIMARY", "AXIAL"]
        ds.SeriesNumber, ds.InstanceNumber = 7, z + 1
        ds.SeriesDescription = "synthetic_ct"
        ds.Rows, ds.Columns = 4, 3
        ds.ImageOrientationPatient = [1, 0, 0, 0, 1, 0]
        ds.ImagePositionPatient = [11, 23, 37 + 4 * z]
        ds.PixelSpacing, ds.SliceThickness = [3, 2], 4
        ds.SpacingBetweenSlices = 4
        ds.SamplesPerPixel, ds.PhotometricInterpretation = 1, "MONOCHROME2"
        ds.BitsAllocated, ds.BitsStored, ds.HighBit = 16, 16, 15
        ds.PixelRepresentation = 1
        ds.RescaleSlope, ds.RescaleIntercept = 2, -1024
        ds.RescaleType = "HU"
        plane = np.array(
            [[100 * z + 10 * y + x for x in range(3)] for y in range(4)], dtype="<i2"
        )
        ds.PixelData = plane.tobytes()
        dcmwrite(source / f"slice-{z}.dcm", ds, enforce_file_format=True)

    non_nifti_to_nifti(str(source), str(output))

    files = list(output.glob("CT_*.nii*"))
    assert len(files) == 1, list(output.iterdir())
    image = nib.load(files[0])
    assert image.shape == (3, 4, 5)
    data = image.get_fdata()
    inverse_affine = np.linalg.inv(image.affine)
    # Independent source geometry: columns advance 2 mm L, rows 3 mm P,
    # slices 4 mm S. NIfTI world axes are RAS, so negate the L/P coordinates.
    for z in range(5):
        for y in range(4):
            for x in range(3):
                ras = np.array([-(11 + 2 * x), -(23 + 3 * y), 37 + 4 * z, 1])
                index = np.rint((inverse_affine @ ras)[:3]).astype(int)
                np.testing.assert_allclose(
                    image.affine @ np.r_[index, 1], ras, rtol=0, atol=1e-6
                )
                assert data[tuple(index)] == 2 * (100 * z + 10 * y + x) - 1024
