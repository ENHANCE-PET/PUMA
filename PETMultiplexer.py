# 1 Get a list of patients
# 2 Get PET and CT per patient
# 2.1 reslice CT to PET
# 3 Get masks per patient for evaluation
# 4 register CTs
# 5 Apply transform and warp to PET and mask image


# Imports
import os
import subprocess
import SimpleITK
import evaluation
import image_processing as imgp
import pandas as pd


# Constants
PET_FOLDER = 'PET'
CT_FOLDER = 'CT'
TRANSFORM_FOLDER = 'transforms'
LABELS_FOLDER = 'labels'

MULTI_RESOLUTION_SCHEME = '100x25x10'
COST_FUNCTION = 'SSD'  # 'NCC 2x2x2'
greedy_version = "/home/horyzen/Projects/builds/Greedy/bin/greedy"

# Indices with Organs
# 4 Brain
# 7 Liver
# 9 spleen
# 12 Lungs

EVALUATION_ORGANS = [4, 7, 9, 12]

main_directory = '/home/horyzen/Downloads/multiplexing/UCD/TracerMultiplexingProject/test_run_batch1'
subjects = os.listdir(main_directory)

all_dice_scores = []

for subject in subjects:
    subject_directory = os.path.join(main_directory, subject)
    tracers = os.listdir(subject_directory)

    if len(tracers) < 1:
        print(f"Not enough tracers to multiplex for {subject}")
        continue

    print(f'Working on patient: {subject}')
    for tracer_index, tracer in enumerate(tracers):
        tracer_directory = os.path.join(subject_directory, tracer)
        tracer_CT_directory = os.path.join(tracer_directory, CT_FOLDER)
        tracer_PET_directory = os.path.join(tracer_directory, PET_FOLDER)
        tracer_label_directory = os.path.join(tracer_directory, LABELS_FOLDER)

        metrics_unaligned = []
        metrics_aligned = []

        # First tracer as reference
        if tracer_index == 0:
            print(f' {tracer} -> REFERENCE: Subsequent tracers are aligned towards it.')
            patient_reference_PET_path = os.path.join(tracer_PET_directory, os.listdir(tracer_PET_directory)[0])

            subject_CT_path = os.path.join(tracer_CT_directory, os.listdir(tracer_CT_directory)[0])
            patient_reference_CT_path = os.path.join(tracer_CT_directory,
                                                     f"PET-ALIGNED_{os.path.basename(subject_CT_path)}")

            print(f'  Reslicing {tracer} CT     to fit {tracer} PET domain')
            imgp.reslice_identity(patient_reference_PET_path, subject_CT_path, patient_reference_CT_path)

            subject_label_path = os.path.join(tracer_label_directory, os.listdir(tracer_label_directory)[0])
            patient_reference_label_path = os.path.join(tracer_label_directory,
                                                        f"PET-ALIGNED_{os.path.basename(subject_label_path)}")
            print(f'  Reslicing {tracer} labels to fit {tracer} PET domain')
            imgp.reslice_identity(patient_reference_PET_path, subject_label_path, patient_reference_label_path,
                                  is_label_image=True)

            print(f'  Reference PET    ({tracer}): {patient_reference_PET_path}')
            print(f'  Reference CT     ({tracer}): {patient_reference_CT_path}')
            print(f'  Reference labels ({tracer}): {patient_reference_label_path}')

        # Each subsequent tracer
        else:
            print(f' {tracer} -> {tracers[0]}')
            patient_current_PET_path = os.path.join(tracer_PET_directory, os.listdir(tracer_PET_directory)[0])

            subject_CT_path = os.path.join(tracer_CT_directory, os.listdir(tracer_CT_directory)[0])
            subject_current_CT_path = os.path.join(tracer_CT_directory,
                                                   f"PET-ALIGNED_{os.path.basename(subject_CT_path)}")

            print(f'  Reslicing {tracer} CT     to fit {tracer} PET domain')
            imgp.reslice_identity(patient_current_PET_path, subject_CT_path, subject_current_CT_path)

            subject_label_path = os.path.join(tracer_label_directory, os.listdir(tracer_label_directory)[0])
            subject_current_label_path = os.path.join(tracer_label_directory,
                                                      f"PET-ALIGNED_{os.path.basename(subject_label_path)}")

            print(f'  Reslicing {tracer} labels to fit {tracer} PET domain')
            imgp.reslice_identity(patient_current_PET_path, subject_label_path, subject_current_label_path,
                                  is_label_image=True)

            print(f'  Current PET     ({tracer}): {patient_current_PET_path}')
            print(f'  Current CT      ({tracer}): {subject_current_CT_path}')
            print(f'  Current labels  ({tracer}): {subject_current_label_path}')

            # Evaluate before alignment
            patient_current_label_unaligned_path = os.path.join(tracer_label_directory,
                                                                f"UNALIGNED_"
                                                                f"{os.path.basename(subject_current_label_path)}")
            imgp.reslice_identity(patient_reference_label_path, subject_current_label_path,
                                  patient_current_label_unaligned_path, is_label_image=True, center_images=True)
            subject_current_PET_unaligned_path = os.path.join(tracer_PET_directory,
                                                              f"UNALIGNED_{os.path.basename(patient_current_PET_path)}")
            imgp.reslice_identity(patient_reference_PET_path, patient_current_PET_path,
                                  subject_current_PET_unaligned_path, is_label_image=False, center_images=True)

            print(f' Before alignment   ({tracer}):')
            print(f'  Reference labels  ({tracer}): {patient_reference_label_path}')
            print(f'  Compare labels    ({tracer}): {patient_current_label_unaligned_path}')
            print(f'  Compare PET       ({tracer}): {subject_current_PET_unaligned_path}')
            reference_labels = SimpleITK.ReadImage(patient_reference_label_path, SimpleITK.sitkUInt8)
            resliced_labels = SimpleITK.ReadImage(patient_current_label_unaligned_path, SimpleITK.sitkUInt8)
            resliced_PET = SimpleITK.ReadImage(subject_current_PET_unaligned_path)

            images = (reference_labels, resliced_labels, resliced_PET)

            for EVALUATION_ORGAN in EVALUATION_ORGANS:
                metrics_unaligned.append(evaluation.evaluate_label(images, EVALUATION_ORGAN))

            # Alignment preparation
            tracer_transform_directory = os.path.join(tracer_directory, TRANSFORM_FOLDER)
            if not os.path.exists(tracer_transform_directory):
                os.mkdir(tracer_transform_directory)
            print(f'  {tracer} transforms will be at {tracer_transform_directory}')

            # Affine alignment
            print(f"  Aligning [affine]     {subject_current_CT_path} -> {patient_reference_CT_path}")
            affine_transform_file_path = os.path.join(tracer_transform_directory,
                                                      f"{subject}_{tracer}-to-{tracers[0]}_affine-transform.mat")
            command_string = f"{greedy_version} " \
                             f"-d 3 " \
                             f"-a " \
                             f"-ia-image-centers " \
                             f"-i {patient_reference_CT_path} {subject_current_CT_path} " \
                             f"-dof 12 " \
                             f"-o {affine_transform_file_path} " \
                             f"-n {MULTI_RESOLUTION_SCHEME} " \
                             f"-m {COST_FUNCTION}"
            subprocess.run(command_string, shell=True, capture_output=True)

            # Deformable alignment
            print(f"  Aligning [deformable] {subject_current_CT_path} -> {patient_reference_CT_path}")
            deformable_transform_file_path = os.path.join(tracer_transform_directory,
                                                          f"{subject}_{tracer}-to-{tracers[0]}_deformable-warp.nii.gz")

            command_string = f"{greedy_version} " \
                             f"-d 3 " \
                             f"-float " \
                             f"-it {affine_transform_file_path} " \
                             f"-i {patient_reference_CT_path} {subject_current_CT_path} " \
                             f"-o {deformable_transform_file_path} " \
                             f"-n {MULTI_RESOLUTION_SCHEME} " \
                             f"-sv " \
                             f"-m {COST_FUNCTION}"
            subprocess.run(command_string, shell=True, capture_output=True)

            # Reslicing PET
            interpolation_type = "LINEAR"
            patient_resliced_PET_path = os.path.join(tracer_PET_directory,
                                                     f"MULTIPLEXED_{tracer}_"
                                                     f"{os.path.basename(patient_current_PET_path)}")
            print(f"  Reslicing: {patient_current_PET_path} -> {patient_resliced_PET_path}")
            print(f"             Reference {patient_reference_PET_path} | Interpolation: {interpolation_type}")

            command_string = f"{greedy_version} " \
                             f"-d 3 " \
                             f"-rf {patient_reference_PET_path} " \
                             f"-ri {interpolation_type} " \
                             f"-rm {patient_current_PET_path} {patient_resliced_PET_path} " \
                             f"-r {deformable_transform_file_path} {affine_transform_file_path}"
            subprocess.run(command_string, shell=True, capture_output=True)

            # Reslicing labels
            interpolation_type = "LABEL 0.2vox"
            patient_resliced_label_path = os.path.join(tracer_label_directory,
                                                       f"MULTIPLEXED_{tracer}_"
                                                       f"{os.path.basename(subject_current_label_path)}")
            print(f"  Reslicing: {subject_current_label_path} -> {patient_resliced_label_path}")
            print(f"             Reference {patient_reference_PET_path} | Interpolation: {interpolation_type}")

            command_string = f"{greedy_version} " \
                             f"-d 3 " \
                             f"-rf {patient_reference_PET_path} " \
                             f"-ri {interpolation_type} " \
                             f"-rm {subject_current_label_path} {patient_resliced_label_path} " \
                             f"-r {deformable_transform_file_path} {affine_transform_file_path}"
            subprocess.run(command_string, shell=True, capture_output=True)

            # Evaluate after alignment
            print(f' After alignment   ({tracer}):')
            print(f'  Reference labels ({tracer}): {patient_reference_label_path}')
            print(f'  Compare labels   ({tracer}): {patient_resliced_label_path}')
            print(f'  Compare PET      ({tracer}): {patient_resliced_PET_path}')
            reference_labels = SimpleITK.ReadImage(patient_reference_label_path, SimpleITK.sitkUInt8)
            resliced_labels = SimpleITK.ReadImage(patient_resliced_label_path, SimpleITK.sitkUInt8)
            resliced_PET = SimpleITK.ReadImage(patient_resliced_PET_path)

            images = (reference_labels, resliced_labels, resliced_PET)

            for EVALUATION_ORGAN in EVALUATION_ORGANS:
                metrics_aligned.append(evaluation.evaluate_label(images, EVALUATION_ORGAN))

            tracer_dice_scores = [subject, tracer]
            print(f' Percentage difference:')
            for i in range(len(EVALUATION_ORGANS)):
                dice_unaligned = float(metrics_unaligned[i][1])
                dice_aligned = float(metrics_aligned[i][1])
                dice_difference_percentage = ((dice_aligned-dice_unaligned)/dice_aligned)*100
                print(f'  DICE score (label {EVALUATION_ORGANS[i]}) %: {dice_difference_percentage}')
                tracer_dice_scores.append(dice_difference_percentage)
            all_dice_scores.append(tracer_dice_scores)

    print('')

print('Saving metrics as csv')
column_names = ['Patient', 'Tracer', 'Brain', 'Liver', 'Spleen', 'Lungs']
metrics_df = pd.DataFrame(all_dice_scores, columns=column_names)
metrics_df.to_csv(os.path.join(main_directory, 'dice_scores.csv'), index=False)

print('FINISHED')
