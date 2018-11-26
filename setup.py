from setuptools import setup

setup(
    name='md2cf',
    version='0.1.0',
    packages=['md2cf'],
    url='https://github.com/iamjackg/md2cf',
    license='MIT',
    author='Jack Gaino',
    author_email='md2cf@jackgaino.com',
    description='Convert Markdown documents to Confluence',
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    keywords='markdown confluence',
    install_requires=[
        'mistune',
        'tortilla',
        'lxml',
        'beautifulsoup4',
    ],
    python_requires='>=3',
    entry_points={
        'console_scripts': [
            'md2cf=md2cf.__main__:main'
        ]
    },
)
