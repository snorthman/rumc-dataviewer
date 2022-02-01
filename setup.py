from setuptools import setup

setup(
    name='RUCMDataViewer',
    version='1.0',
    packages=['viewer'],
    url='',
    license='',
    author='C.R. Noordman',
    author_email='stan.noordman@radboudumc.nl',
    description='View data downloaded from RUMC',
    install_requires=['dearpygui', 'SimpleITK', 'thefuzz'],
)
