from setuptools import setup
from setuptools import find_packages

setup(
    name='securedrop',
    version='1.0',
    packages=find_packages(),
    url='https://github.com/aokellermann/securedrop',
    license='MIT License',
    author='Antony Kellermann',
    author_email='aokellermann@gmail.com',
    description='Secure file sharing command line application.',
    python_requires='>=3.8',
    install_requires=[
        'certifi>=2020.11.8',
        'chardet>=3.0.4',
        'crypto>=1.4.1',
        'dnspython>=2.0.0',
        'email-validator>=1.1.2',
        'idna>=2.10',
        'Naked>=0.1.31',
        'Padding>=0.5',
        'pycryptodome>=3.9.9',
        'PyYAML>=5.3.1',
        'requests>=2.25.0',
        'securedrop>=1.0',
        'shellescape>=3.8.1',
        'tornado>=6.1'
        'urllib3>=1.26.2',
        'yapf>=0.30.0'
    ],

)
