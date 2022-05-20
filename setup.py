from setuptools import setup

setup(
    name='rumc_dataviewer',
    version='1.1.0',
    url='https://github.com/snorthman/rumc_dataviewer/',
    license='MIT',
    author='C.R. Noordman',
    author_email='stan.noordman@radboudumc.nl',
    description='View and setup data downloaded from RUMC',
    python_requires='>=3.6',
    install_requires=[
        'click~=8.1',
        'dearpygui~=1.3',
        'numpy~=1.22',
        'pandas~=1.4',
        'pydicom~=2.2',
        'pylibjpeg-libjpeg~=1.3',
        'SimpleITK~=2.1',
        'tqdm~=4.63',
        'GDCM~=1.1',
        'pylibjpeg~=1.4'
    ],
    entry_points={
        'console_scripts': [
            'dataviewer = dataviewer:cli',
        ]
    }
)
