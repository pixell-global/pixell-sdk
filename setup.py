from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="pixell-kit",
    version="0.2.9",
    author="Pixell Core Team",
    author_email="dev@pixell.global",
    description="A lightweight developer kit for packaging AI agents into portable APKG files",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/pixell-global/pixell-kit",
    project_urls={
        "Bug Tracker": "https://github.com/pixell-global/pixell-kit/issues",
        "Documentation": "https://docs.pixell.global/pixell",
        "Source Code": "https://github.com/pixell-global/pixell-kit",
    },
    packages=find_packages(include=['pixell', 'pixell.*']),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Build Tools",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: OS Independent",
    ],
    license="Apache-2.0",
    python_requires=">=3.11",
    install_requires=[
        "click>=8.0",
        "pydantic>=2.0",
        "pyyaml>=6.0",
        "jsonschema>=4.0",
        "fastapi>=0.100.0",
        "uvicorn>=0.23.0",
        "watchdog>=3.0",
        "python-dotenv>=1.0",
        "tabulate>=0.9",
        "jinja2>=3.0",
        "requests>=2.31.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0",
            "pytest-cov>=4.0",
            "pytest-asyncio>=0.21",
            "black>=23.0",
            "mypy>=1.0",
            "ruff>=0.1",
        ],
        "signing": [
            "python-gnupg>=0.5",
        ],
    },
    entry_points={
        "console_scripts": [
            "pixell=pixell.cli.main:cli",
        ],
    },
    include_package_data=True,
    zip_safe=False,
)