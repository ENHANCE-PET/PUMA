from setuptools import setup, find_packages


setup(
    name='pumaz',
    version='1.7.8',
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
        'nibabel',
        'halo',
        'SimpleITK',
        'pydicom',
        'numpy',
        'mpire',
        'openpyxl',
        'matplotlib',
        'pyfiglet',
        'natsort',
        'colorama',
        'rich',
        'pandas',
        'dicom2nifti',
        'nifti2dicom',
        'requests',
        'moosez',
        'halo',
        'psutil',
        'gputil',
        'dask'
    ],
    entry_points={
        'console_scripts': [
            'pumaz=pumaz.pumaz:main',
        ],
    },
)
