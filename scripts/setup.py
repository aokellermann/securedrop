from setuptools import setup
from setuptools import find_packages

setup(
    name='securedrop',
    version='1.0',
    packages=find_packages(),
    url='https://github.com/aokellermann/securedrop',
    license='MIT License',
    author='Antony Kellermann',
    author_email='antony_kellermann@student.uml.edu',
    description='Secure file sharing command line application.',
    python_requires='>=3.8',
    install_requires=[
        'Naked>=0.1.31',
        'Padding>=0.5',
        'PyYAML>=5.3.1',
        'certifi>=2020.11.8',
        'chardet>=3.0.4',
        'crypto>=1.4.1',
        'dnspython>=2.0.0',
        'email-validator>=1.1.2',
        'idna>=2.10',
        'pycryptodome>=3.9.9',
        'requests>=2.25.0',
        'setuptools>=50.3.2',
        'shellescape>=3.8.1',
        'tornado>=6.1',
        'urllib3>=1.26.2',
        'yapf>=0.30.0'
    ],

)
