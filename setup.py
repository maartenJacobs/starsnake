import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="starsnake",
    version="0.0.0",
    author="Maarten Jacobs",
    author_email="maarten.j.jacobs@gmail.com",
    description="Gemini client library",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/maartenJacobs/starsnake",
    packages=setuptools.find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Topic :: Utilities",
        "Topic :: Internet",
    ],
    python_requires="~=3.7",  # Python >= 3.7 but < 4
    keywords=["gemini", "starsnake"],
)
