# Imports
import os
import subprocess


# Constants
PET_FOLDER = 'PET'
CT_FOLDER = 'CT'
TRANSFORM_FOLDER = 'transforms'
LABELS_FOLDER = 'labels'

COST_FUNCTION = 'SSD'
MULTI_RESOLUTION_SCHEME = '100x25x10'
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
            subprocess_call = f"dcm2niix " \
                              f"-z y " \
                              f"-f {CT_FOLDER} " \
                              f"{tracer_CT_directory}"
            subprocess.run(subprocess_call, shell=True, capture_output=True)

            tracer_PET_directory = os.path.join(tracer_directory, PET_FOLDER)
            subprocess_call = f"dcm2niix " \
                              f"-z y " \
                              f"-f {PET_FOLDER} " \
                              f"{tracer_PET_directory}"
            subprocess.run(subprocess_call, shell=True, capture_output=True)
