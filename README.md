# Starsnake

WIP Gemini client library for Python 3.

Ever thought the modern web was a bit bloated? Try Gemini (or Gopher). Gemini is a simple protocol to browse
the web. Unlike Gopher it uses TLS by default so no one is intercepting your browsing.

## Usage

1. Import the library using `from starsnake import client`.
2. To make a request use `header, response = client.sync_request(url)`.
3. Assume success and print the response, `if header.category == client.Category.SUCCESS:
    print(b"\n".join(cast(List[bytes], response)).decode())`.

## Examples

### Curl

`examples/curl/` is a CLI tool to make Gemini requests and print the response.
For example, `PYTHONPATH=. python examples/curl/main.py gemini://gemini.circumlunar.space/` will
print the page hosted on `gemini://gemini.circumlunar.space/`.

Note that this curl-ripoff will store files `~/.starsnake/`.

This tool is the main way I browse Geminispace at the moment so it's subject to much change.

### Async downloader

`examples/downloader/` is a CLI tool that downloads all content under an Gemini path.

For example:

```shell script
PYTHONPATH=. python examples/curl/main.py gemini://gemini.circumlunar.space/users/wakyct/
```

The above will download all pages hosted under `gemini://gemini.circumlunar.space/users/wakyct/`, including
those in nested paths. The tool won't go back up to the root, and sleeps between 100ms and 500ms (per worker) to
prevent making too requests (not guaranteed though; the decision to sleep needs to move elsewhere).

Downloaded files are, by default, stored in a new subdirectory in the current directory. The new subdirectory
is the hostname of the original path, i.e. `./<hostname>/`. Under this subdirectory, each path and hosted page
is recreated. This means `gemini://gemini.circumlunar.space/users/wakyct/` will result in, at least, the
following structure:

```
gemini.circumlunar.space/
    users/
        wakyct/
            index.gmi
```

Similar to the Curl-like tool, this tool will store files `~/.starsnake/`.

## Development

### Requirements

You'll need to install Python 3.7 and 3.8. `pyenv` is a good option to install multiple Python versions.

Then install `tox`, which will run the linting and tests for both Python 3.7 and 3.8.

```shell script
pip install 'tox==3.17.*'
```

### Commands

Run `tox` to run all of the linters and tests:

```shell script
tox
```

### Virtual environments

If you need a virtual environment outside of the `tox` commands above (e.g. for your IDE), you can also use
`tox` to create an environment for you. The following command creates a virtual environment in `./venv-py38`.

```shell script
tox --devenv venv-py38 -e py38
```
