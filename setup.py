from setuptools import setup, find_packages

setup(
    name="mailcoach_lite",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "mailbox",
        "litellm"
    ],
    author="Wei Dong",
    author_email="wdong@aaalgo.com",
    description="Mailcoach lite library",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/aaalgo/mailcoach_lite",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: BSD License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.7",
)
