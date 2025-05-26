#!/usr/bin/env python3
"""
Read URLs from urls.txt and output a Python module
that defines `video_urls = [...]`.
"""

from pathlib import Path


def main():
    input_file = "urls.txt"
    output_file = "formatted12345678_urls.py"

    # Read and clean URLs
    urls = Path(input_file).read_text().splitlines()
    urls = [url.strip() for url in urls if url.strip()]

    # Join into a Python list literal
    formatted = ",\n".join(f"'{u}'" for u in urls)

    # Write out the module
    data = (
        "video_urls = [\n"
        f"{formatted}\n"
        "]\n"
    )
    Path(output_file).write_text(data)
    print(f"Formatted URLs have been saved to {output_file}")


if __name__ == "__main__":
    main()
