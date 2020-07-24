# Gemini site downloader

Download all pages of a Gemini site.

## Usage

```shell script
PYTHONPATH=. python -m downloader <url> [<output_directory>]
```

The above will download all pages hosted at the URL and store them in
`output_directory/<url_hostname>/`. The tool will have created directories and files in this
base directory: paths of the requested pages become directories and the document name will
become the file. Note that a missing document name, e.g. `gemini://foo.bar/hello/`, defaults
to `index.<extension>`, which is somewhat of a convention on the web and Geminispace.
