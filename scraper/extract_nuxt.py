"""
Extract Roland Garros Nuxt.js server-state data as clean JSON.

The RG website embeds all match/draw/player data server-side in a
`window.__NUXT__=(function(...){...})()` IIFE within a <script> tag.

Strategy:
  1. Fetch the HTML page via requests
  2. Extract the raw <script> text via regex
  3. Write a temp .js that mocks `global.window`, runs the IIFE,
     and dumps `window.__NUXT__` as JSON via stdout
  4. Read and parse the JSON in Python
"""

import json
import os
import re
import subprocess
import tempfile
from pathlib import Path

import requests

SCRIPT_TEMPLATE = """\
global.window = {{}};
{nuxt_js}
console.log(JSON.stringify(window.__NUXT__));
"""

NUXT_MARKER = "window.__NUXT__"


class NuxtExtractionError(Exception):
    """Raised when __NUXT__ data cannot be extracted from the page."""


def fetch_page(url: str, timeout: int = 15) -> str:
    """Fetch an RG page. Returns raw HTML."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
        ),
    }
    resp = requests.get(url, headers=headers, timeout=timeout)
    resp.raise_for_status()
    return resp.text


def extract_nuxt_js(html: str) -> str:
    """Extract the raw JS text of the window.__NUXT__ assignment."""
    pos = html.find(NUXT_MARKER)
    if pos == -1:
        raise NuxtExtractionError("Could not find __NUXT__ marker in HTML")
    
    # Find the <script> tag that contains this marker
    script_start = html.rfind("<script", 0, pos)
    if script_start == -1:
        raise NuxtExtractionError("Could not find <script> before __NUXT__")
    
    # Find the </script> tag after the marker
    script_end = html.find("</script>", pos)
    if script_end == -1:
        raise NuxtExtractionError("Could not find </script> after __NUXT__")
    script_end += len("</script>")
    
    raw = html[script_start:script_end]
    # Strip the <script> tags
    inner = raw.removeprefix("<script>").removesuffix("</script>").strip()
    return inner


def evaluate_nuxt_js(nuxt_js: str, node_path: str = "node") -> dict:
    """
    Evaluate the __NUXT__ JavaScript in Node.js and return the parsed dict.
    
    Works by wrapping the JS in a small script that mocks `global.window`,
    runs the IIFE, and dumps `window.__NUXT__` via stdout.
    """
    full_script = SCRIPT_TEMPLATE.format(nuxt_js=nuxt_js)
    
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".js", delete=False
    ) as f:
        f.write(full_script)
        tmp_path = f.name

    try:
        result = subprocess.run(
            [node_path, tmp_path],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            raise NuxtExtractionError(
                f"Node.js evaluation failed (rc={result.returncode}):\n"
                f"STDERR: {result.stderr[:500]}"
            )
        data = json.loads(result.stdout)
        return data
    except json.JSONDecodeError as e:
        raise NuxtExtractionError(
            f"Failed to parse Node.js output as JSON: {e}\n"
            f"STDOUT (first 500 chars): {result.stdout[:500]}"
        )
    finally:
        os.unlink(tmp_path)


def fetch_nuxt_data(url: str, timeout: int = 15) -> dict:
    """
    High-level: fetch a page → extract __NUXT__ JS → evaluate → return dict.
    """
    html = fetch_page(url, timeout=timeout)
    nuxt_js = extract_nuxt_js(html)
    return evaluate_nuxt_js(nuxt_js)


# ─── Convenience: known RG data URLs ───────────────────────────────────────

def draw_url(draw_code: str = "SM", year: int = 2026, round_num: int = 1) -> str:
    """URL for a specific draw page."""
    return f"https://www.rolandgarros.com/en-us/results/{draw_code}?round={round_num}"


def players_url(sex: str = "M", year: int = 2026) -> str:
    """URL for the players directory."""
    return f"https://www.rolandgarros.com/en-us/players?sex={sex}"


# ─── CLI entry point ────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    url = sys.argv[1] if len(sys.argv) > 1 else draw_url()
    print(f"Fetching: {url}", file=sys.stderr)
    data = fetch_nuxt_data(url)
    json.dump(data, sys.stdout, indent=2, ensure_ascii=False)
