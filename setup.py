from setuptools import setup, find_packages

setup(
    name='easym4b',
    version='0.1',
    description='Split M4B files into MP3 chapters based on metadata.',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'click',
        'ffmpeg-python',
        'tqdm',
        'python-slugify',
    ],
    entry_points={
        'console_scripts': [
            'easym4b=easym4b.main:main',
        ],
    },
    license='Mozilla Public License 2.0',
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: Mozilla Public License 2.0 (MPL 2.0)',
        'Operating System :: OS Independent',
    ],
)