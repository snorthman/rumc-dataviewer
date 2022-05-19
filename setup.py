from setuptools import setup, find_packages

setup(
    name='RUCMDataViewer',
    version='1.0.2',
    url='https://github.com/snorthman/RUMCDataViewer/',
    license='MIT',
    author='C.R. Noordman',
    author_email='stan.noordman@radboudumc.nl',
    description='View and setup data downloaded from RUMC',
    packages=find_packages(),
    include_package_data=True,
    entry_points={
        'console_scripts': [
            'dataviewer = dataviewer:cli',
        ]
    }
)
