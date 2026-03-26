from setuptools import find_packages, setup

setup(
    name="watchagent",
    version="0.1.0",
    description="Debugger and monitor for AI agents",
    packages=find_packages(),
    include_package_data=True,
    python_requires=">=3.9",
    entry_points={
        "console_scripts": [
            "watchagent=watchagent.cli:main",
        ]
    },
)
