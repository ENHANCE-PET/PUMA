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
# 12 Lungs
# 7 Liver
# 3 bladder
# 9 spleen

EVALUATION_ORGANS = [3, 4, 7, 9, 12]

main_directory = '/home/horyzen/Downloads/multiplexing/UCD/TracerMultiplexingProject/test_run'

# 1 Get a list of patients
patients = os.listdir(main_directory)

for patient in patients:
    patient_directory = os.path.join(main_directory, patient)
    tracers = os.listdir(patient_directory)

    print(f'Working on patient: {patient}')
    if len(tracers) > 1:
        for tracer_index, tracer in enumerate(tracers):
            tracer_directory = os.path.join(patient_directory, tracer)
            tracer_CT_directory = os.path.join(tracer_directory, CT_FOLDER)
            tracer_PET_directory = os.path.join(tracer_directory, PET_FOLDER)
            tracer_label_directory = os.path.join(tracer_directory, LABELS_FOLDER)

            if tracer_index == 0:
                print(f' {tracer} -> REFERENCE: Subsequent tracers are aligned towards it.')
                patient_reference_PET_path = os.path.join(tracer_PET_directory, os.listdir(tracer_PET_directory)[0])

                patient_CT_path = os.path.join(tracer_CT_directory, os.listdir(tracer_CT_directory)[0])
                patient_reference_CT_path = os.path.join(tracer_CT_directory,
                                                         f"PET-ALIGNED_{os.path.basename(patient_CT_path)}")
                if not os.path.exists(patient_reference_CT_path):
                    print(f'  Reslicing {tracer} CT to fit {tracer} PET domain')
                    command_string = f"c3d {patient_reference_PET_path} {patient_CT_path} " \
                                     f"-reslice-identity " \
                                     f"-o {patient_reference_CT_path}"
                    subprocess.run(command_string, shell=True, capture_output=True)
                else:
                    print(f'  Resliced {tracer} CT already exists.')

                patient_label_path = os.path.join(tracer_label_directory, os.listdir(tracer_label_directory)[0])
                patient_reference_label_path = os.path.join(tracer_label_directory,
                                                            f"PET-ALIGNED_{os.path.basename(patient_label_path)}")
                if not os.path.exists(patient_reference_label_path):
                    print(f'  Reslicing {tracer} labels to fit {tracer} PET domain')
                    command_string = f"c3d {patient_reference_PET_path} {patient_label_path} " \
                                     f"-reslice-identity " \
                                     f"-o {patient_reference_label_path}"
                    subprocess.run(command_string, shell=True, capture_output=True)
                else:
                    print(f'  Resliced {tracer} labels already exists.')

                print(f'  Reference CT     ({tracer}): {patient_reference_CT_path}')
                print(f'  Reference PET    ({tracer}): {patient_reference_PET_path}')
                print(f'  Reference labels ({tracer}): {patient_reference_label_path}')

            else:
                print(f' {tracer} -> {tracers[0]}')
                tracer_transform_directory = os.path.join(tracer_directory, TRANSFORM_FOLDER)
                if not os.path.exists(tracer_transform_directory):
                    os.mkdir(tracer_transform_directory)
                print(f'  {tracer} transforms will be at {tracer_transform_directory}')

                patient_current_PET_path = os.path.join(tracer_PET_directory, os.listdir(tracer_PET_directory)[0])
                patient_CT_path = os.path.join(tracer_CT_directory, os.listdir(tracer_CT_directory)[0])
                patient_current_CT_path = os.path.join(tracer_CT_directory,
                                                       f"PET-ALIGNED_{os.path.basename(patient_CT_path)}")

                if not os.path.exists(patient_current_CT_path):
                    print(f'  Reslicing {tracer} CT to fit {tracer} PET domain')
                    command_string = f"c3d {patient_current_PET_path} {patient_CT_path} " \
                                     f"-reslice-identity " \
                                     f"-o {patient_current_CT_path}"
                    subprocess.run(command_string, shell=True, capture_output=True)
                else:
                    print(f'  Resliced {tracer} CT already exists.')

                print(f'  Current CT  ({tracer}): {patient_current_CT_path}')
                print(f'  Current PET ({tracer}): {patient_current_PET_path}')

                # Affine alignment
                print(f"  Aligning [affine]     {patient_current_CT_path} -> {patient_reference_CT_path}")
                affine_transform_file_path = os.path.join(tracer_transform_directory,
                                                          f"{patient}_{tracer}-to-{tracers[0]}_affine-transform.mat")
                command_string = f"{greedy_version} " \
                                 f"-d 3 " \
                                 f"-a " \
                                 f"-ia-image-centers " \
                                 f"-i {patient_reference_CT_path} {patient_current_CT_path} " \
                                 f"-dof 12 " \
                                 f"-o {affine_transform_file_path} " \
                                 f"-n {MULTI_RESOLUTION_SCHEME} " \
                                 f"-m {COST_FUNCTION}"
                subprocess.run(command_string, shell=True, capture_output=True)

                # Deformable alignment
                print(f"  Aligning [deformable] {patient_current_CT_path} -> {patient_reference_CT_path}")
                deformable_transform_file_path = os.path.join(tracer_transform_directory,
                                                              f"{patient}_{tracer}-to-{tracers[0]}_deformable-warp.nii.gz")

                command_string = f"{greedy_version} " \
                                 f"-d 3 " \
                                 f"-float " \
                                 f"-it {affine_transform_file_path} " \
                                 f"-i {patient_reference_CT_path} {patient_current_CT_path} " \
                                 f"-o {deformable_transform_file_path} " \
                                 f"-n {MULTI_RESOLUTION_SCHEME} " \
                                 f"-sv " \
                                 f"-m {COST_FUNCTION}"
                subprocess.run(command_string, shell=True, capture_output=True)

                # Reslicing PET
                interpolation_type = "LINEAR"
                patient_resliced_PET_image = os.path.join(tracer_PET_directory,
                                                          f"MULTIPLEXED_{patient}_{tracer}-to-{tracers[0]}_{os.path.basename(patient_current_PET_path)}")
                print(f"  Reslicing: {patient_current_PET_path} -> {patient_resliced_PET_image}")
                print(f"             Reference {patient_reference_PET_path} | Interpolation: {interpolation_type}")

                command_string = f"{greedy_version} " \
                                 f"-d 3 " \
                                 f"-rf {patient_reference_PET_path} " \
                                 f"-ri {interpolation_type} " \
                                 f"-rm {patient_current_PET_path} {patient_resliced_PET_image} " \
                                 f"-r {deformable_transform_file_path} {affine_transform_file_path}"
                subprocess.run(command_string, shell=True, capture_output=True)

                # label preparation
                patient_label_path = os.path.join(tracer_label_directory, os.listdir(tracer_label_directory)[0])
                patient_current_label_path = os.path.join(tracer_label_directory,
                                                          f"PET-ALIGNED_{os.path.basename(patient_label_path)}")
                if not os.path.exists(patient_current_label_path):
                    print(f'  Reslicing {tracer} labels to fit PET domain')
                    command_string = f"c3d {patient_current_PET_path} {patient_label_path} " \
                                     f"-reslice-identity " \
                                     f"-o {patient_current_label_path}"
                    subprocess.run(command_string, shell=True, capture_output=True)
                else:
                    print(f'  Resliced {tracer} labels already exist.')

                # Reslicing labels
                interpolation_type = "LABEL 0.2vox"
                patient_resliced_label_image = os.path.join(tracer_label_directory,
                                                            f"MULTIPLEXED_{patient}_{tracer}-to-{tracers[0]}_{os.path.basename(patient_current_label_path)}")
                print(f"  Reslicing: {patient_current_label_path} -> {patient_resliced_label_image}")
                print(f"             Reference {patient_reference_PET_path} | Interpolation: {interpolation_type}")

                command_string = f"{greedy_version} " \
                                 f"-d 3 " \
                                 f"-rf {patient_reference_PET_path} " \
                                 f"-ri {interpolation_type} " \
                                 f"-rm {patient_current_label_path} {patient_resliced_label_image} " \
                                 f"-r {deformable_transform_file_path} {affine_transform_file_path}"
                subprocess.run(command_string, shell=True, capture_output=True)

                # Evaluate
                print(f' After alignment  ({tracer}):')
                print(f'  Reference labels ({tracer}): {patient_reference_label_path}')
                print(f'  Compare labels   ({tracer}): {patient_resliced_label_image}')
                print(f'  Compare PET      ({tracer}): {patient_resliced_PET_image}')
                reference_labels = SimpleITK.ReadImage(patient_reference_label_path, SimpleITK.sitkUInt8)
                resliced_labels = SimpleITK.ReadImage(patient_resliced_label_image, SimpleITK.sitkUInt8)
                resliced_PET = SimpleITK.ReadImage(patient_resliced_PET_image)

                images = (reference_labels, resliced_labels, resliced_PET)

                for EVALUATION_ORGAN in EVALUATION_ORGANS:
                    evaluation.evaluate_label(images, EVALUATION_ORGAN)

        print('')
    else:
        print(f"Not enough tracers to multiplex for {patient}")
