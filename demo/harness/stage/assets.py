"""Content-versioned HTML shared by credential-independent viewers."""
import hashlib
from pathlib import Path
import re

STATIC = Path(__file__).parent / 'static'


def versioned_html(name, static=STATIC):
    def asset(match):
        url = match.group('url')
        path = (static / url.removeprefix('/static/')).resolve()
        if not path.is_relative_to(static.resolve()) or not path.is_file():
            return match.group(0)
        return f'{match.group("attribute")}{url}?v={hashlib.sha256(path.read_bytes()).hexdigest()[:16]}'
    return re.sub(r'(?P<attribute>(?:src|href)=[\"\x27])(?P<url>/static/[^\"\x27?]+\.(?:js|css))(?:\?[^\"\x27]*)?',
                  asset, (static / name).read_text())
