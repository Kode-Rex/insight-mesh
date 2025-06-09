from setuptools import setup, find_packages

setup(
    name="weave",
    version="0.1.2",
    description="A Rails-like framework for rapidly building and deploying enterprise-grade GenAI applications",
    packages=find_packages(),
    install_requires=[
        "click",
        "rich",
        "python-dotenv",
    ],
    entry_points={
        "console_scripts": [
            "weave=bin.modules.cli:cli",
        ],
    },
    python_requires=">=3.8",
) 