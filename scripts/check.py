from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

root = Path(__file__).resolve().parents[1] / 'docs'
expected = {'index.html', 'support.html'} | {
    f'{skill}/{page}.html'
    for skill in ['azimti', 'al-faza', 'baloot']
    for page in ['privacy', 'terms']
}
assert {p.relative_to(root).as_posix() for p in root.rglob('*.html')} == expected


class Page(HTMLParser):
    def __init__(self, source):
        super().__init__()
        self.ids, self.links = set(), []
        self.arabic = self.english = self.viewport = False
        self.feed(source)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        assert tag not in {'script', 'form', 'iframe'}, f'Unexpected {tag}'
        assert not any(key.startswith('on') for key in attrs), 'Inline event handler'
        if tag == 'html':
            self.arabic = attrs.get('lang') == 'ar' and attrs.get('dir') == 'rtl'
        if attrs.get('lang') == 'en' and attrs.get('dir') == 'ltr':
            self.english = True
        if tag == 'meta' and attrs.get('name') == 'viewport':
            self.viewport = True
        if attrs.get('id'):
            assert attrs['id'] not in self.ids, 'Duplicate anchor'
            self.ids.add(attrs['id'])
        for key in ['href', 'src']:
            if attrs.get(key):
                value = attrs[key]
                if tag != 'a':
                    assert not urlsplit(value).scheme and not value.startswith('//'), 'Remote asset'
                self.links.append(value)


pages = {}
for name in sorted(expected):
    source = (root / name).read_text()
    assert 'example.invalid' not in source and 'alexa@ahmed-ibrahim.com' in source, name
    page = Page(source)
    assert page.arabic and page.english and page.viewport, name
    pages[name] = page

for name, page in pages.items():
    for value in page.links:
        url = urlsplit(value)
        if url.scheme:
            assert url.scheme in {'https', 'mailto'}, value
            continue
        assert not url.netloc, value
        target = (root / name).parent / unquote(url.path) if url.path else root / name
        target = target.resolve()
        assert target.is_relative_to(root.resolve()) and target.is_file(), f'{name}: {value}'
        if url.fragment:
            target_name = target.relative_to(root).as_posix()
            assert url.fragment in pages[target_name].ids, f'{name}: missing anchor {value}'

print(f'{len(pages)} bilingual policy/support pages: links, anchors, local assets and contact checked')
