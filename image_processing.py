import subprocess


def reslice_identity(reference_image_path, image_path, output_image_path):
    command_string = f"c3d {reference_image_path} {image_path} " \
                     f"-reslice-identity " \
                     f"-o {output_image_path}"
    subprocess.run(command_string, shell=True, capture_output=True)