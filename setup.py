from setuptools import setup, find_packages


setup(
    name='pumaz',
    version='1.6.4',
    author='Lalith Kumar Shiyam Sundar, Sebastian Gutschmayer, Manuel Pires',
    author_email='Lalith.shiyamsundar@meduniwien.ac.at, Sebastian.Gutschmayer@meduniwien.ac.at, '
                 'Manuel.pires@meduniwien.ac.at',
    description='PUMA (PET Universal Multi-tracer Aligner) is a robust and efficient tool for aligning images from '
                'different PET tracers. It leverages advanced diffeomorphic imaging techniques to offer high-precision '
                'alignment for multiplexed tracer images. PUMA aims to significantly enhance the accuracy and '
                'reproducibility of PET image studies.',
    python_requires='>=3.10',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    url='https://github.com/QIMP-Team/PUMA',
    license='GPLv3',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Intended Audience :: Healthcare Industry',
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python :: 3 :: Only',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Topic :: Scientific/Engineering :: Medical Science Apps.',
    ],

    keywords='PET tracer alignment, diffeomorphic imaging, image processing, multiplexed tracers',
    packages=find_packages(),
    install_requires=[
        'nibabel~=3.2.2',
        'halo~=0.0.31',
        'SimpleITK~=2.2.1',
        'pydicom~=2.2.2',
        'argparse~=1.4.0',
        'numpy<2.0',
        'mpire~=2.3.3',
        'openpyxl~=3.0.9',
        'matplotlib',
        'pyfiglet~=0.8.post1',
        'natsort~=8.1.0',
        'pillow>=9.2.0',
        'colorama~=0.4.6',
        'rich',
        'pandas',
        'dicom2nifti',
        'nifti2dicom',
        'requests',
        'moosez',
        'halo',
        'psutil',
        'gputil',
        'dask',
        'lionz'
    ],
    entry_points={
        'console_scripts': [
            'pumaz=pumaz.pumaz:main',
        ],
    },
)
