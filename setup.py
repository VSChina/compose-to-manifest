import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="compose-to-manifest",
    version="0.0.1",
    author="typeli",
    author_email="juncli@outlook.com",
    description="Convert Docker Compose project to Azure IoT Edge deployment manifest",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://https://github.com/VSChina/compose-to-manifest",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
    ],
    entry_points={
        "console_scripts": ["compose-to-manifest=convertor.convertor:main"],
    }
)
