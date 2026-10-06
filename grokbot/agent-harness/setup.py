#!/usr/bin/env python3
"""Install the Grok Bot CLI harness."""

from pathlib import Path
from setuptools import find_namespace_packages, setup

with (Path(__file__).parent / "cli_anything/grokbot/README.md").open(encoding="utf-8") as handle:
    long_description = handle.read()

setup(
    name="cli-anything-grokbot",
    version="1.2.1",
    url="https://github.com/ilovebamboo/cli-anything-grokbot",
    license="Apache-2.0",
    license_files=["LICENSE", "NOTICE"],
    classifiers=["Operating System :: MacOS", "Development Status :: 3 - Alpha"],
    description="Grok Bot chat control through the real Electron renderer over loopback CDP.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_namespace_packages(include=["cli_anything.*"], exclude=["cli_anything.grokbot.tests"]),
    python_requires=">=3.10",
    install_requires=["click>=8.0.0", "websocket-client>=1.8,<2"],
    extras_require={"dev": ["pytest>=7.0.0"]},
    entry_points={
        "console_scripts": [
            "cli-anything-grokbot=cli_anything.grokbot.grokbot_cli:main",
        ],
    },
    package_data={"cli_anything.grokbot": ["skills/*.md", "utils/chat_dom.js", "utils/bot_bridge.js"]},
    include_package_data=True,
    zip_safe=False,
)
