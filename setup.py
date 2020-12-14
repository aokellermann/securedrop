from setuptools import find_packages
from setuptools import setup

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
        'certifi>=2020.12.5',
        'chardet>=3.0.4',
        'dnspython>=2.0.0',
        'email-validator>=1.1.2',
        'idna>=2.10',
        'Naked>=0.1.31',
        'nest>asyncio==1.4.3',
        'pycryptodome>=3.9.9',
        'PyYAML>=5.3.1',
        'requests>=2.25.0',
        'shellescape>=3.8.1',
        'tornado>=6.1',
        'urllib3>=1.26.2',
    ],
    scripts=["bin/securedrop", "bin/securedrop_server"]
)
