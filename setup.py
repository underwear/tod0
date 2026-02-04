from setuptools import setup, find_packages

exec(open("todocli/__init__.py").read())

setup(
    name="microsoft-todo-cli",
    version=__version__,
    author="underwear",
    author_email="",
    packages=find_packages(),
    url="https://github.com/underwear/microsoft-todo-cli",
    license="MIT",
    description="Fast, minimal command-line client for Microsoft To-Do",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    install_requires=[
        "pyyaml",
        "requests>=2.28.1",
        "requests_oauthlib",
    ],
    include_package_data=True,
    entry_points={
        "console_scripts": [
            "todo=todocli.cli:main",
        ],
    },
    python_requires=">=3.10",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Topic :: Utilities",
    ],
    keywords="microsoft todo cli task management",
)
