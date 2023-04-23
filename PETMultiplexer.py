# 1 Get a list of patients
# 2 Get PET and CT per patient
# 2.1 reslice CT to PET
# 3 Get masks per patient for evaluation
# 4 register CTs
# 5 Apply transform and warp to PET and mask image


# Imports
import os
import subprocess

# Constants
PET_FOLDER = 'PET'
CT_FOLDER = 'CT'
TRANSFORM_FOLDER = 'transforms'
LABELS_FOLDER = 'labels'

MULTI_RESOLUTION_SCHEME = '100x25x10'
COST_FUNCTION = 'NCC 2x2x2'  # 'SSD'
greedy_version = "/home/horyzen/Projects/builds/Greedy/bin/greedy"

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

                print(f'  Reference CT  ({tracer}): {patient_reference_CT_path}')
                print(f'  Reference PET ({tracer}): {patient_reference_PET_path}')

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

                '''
                # label preparation
                tracer_label_directory = os.path.join(tracer_directory, LABELS_FOLDER)
                patient_label_path = os.path.join(tracer_label_directory, os.listdir(tracer_label_directory)[0])
                patient_current_label_path = os.path.join(patient_label_path,
                                                          f"PET-ALIGNED_{os.path.basename(patient_label_path)}")
                if not os.path.exists(patient_current_label_path):
                    print(f'  Reslicing {tracer} labels to fit PET domain')
                    command_string = f"c3d {patient_current_PET_path} {patient_label_path} " \
                                     f"-reslice-identity " \
                                     f"-o {patient_current_label_path}"
                    # subprocess.run(command_string, shell=True, capture_output=True)
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
                # subprocess.run(command_string, shell=True, capture_output=True)

                # Analysis can go here
                '''

        print('')
    else:
        print(f"Not enough tracers to multiplex for {patient}")
