from setuptools import setup
from distutils.util import convert_path

ver = {}
ver_path = convert_path('dataviewer/version.py')
with open(ver_path) as ver_file:
    exec(ver_file.read(), ver)

setup(
    name='rumc-dataviewer',
    version=ver['__version__'],
    url='https://github.com/snorthman/rumc_dataviewer/',
    license='MIT',
    author='C.R. Noordman',
    author_email='stan.noordman@radboudumc.nl',
    description='View and setup data downloaded from RUMC',
    python_requires='>=3.6',
    packages=['dataviewer'],
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
