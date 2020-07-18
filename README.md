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
