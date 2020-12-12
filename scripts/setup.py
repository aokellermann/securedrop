from setuptools import setup

setup(
    name='securedrop',
    version='1.0',
    packages=['securedrop', 'securedrop.tests'],
    url='https://github.com/aokellermann/securedrop.git',
    license='MIT License',
    author='John Nay, Antony Kellermann, Robert Liani',
    author_email='John_Nay@student.uml.edu',
    description='Secure file sharing command line application.',
    python_requires='>=3.8',
)
