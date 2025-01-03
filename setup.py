from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="rss-news-summarizer",
    version="0.1.0",
    author="Jing He",
    author_email="jinghenowhere@gmail.com",
    description="A RSS feed news summarizer with word clouds and topic clustering",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/hejing3283/rss-news-summarizer",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.7",
    install_requires=requirements,
    include_package_data=True,
    package_data={
        "": ["templates/*.html"],
    },
) 