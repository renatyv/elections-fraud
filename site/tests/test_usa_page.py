"""Check the integrated report and protect it from snapshot builders."""
import ast
from html.parser import HTMLParser
from pathlib import Path
import unittest
from unittest.mock import Mock
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[2]
PAGE = ROOT / 'site/usa-2024/index.html'


class PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.ids: list[str] = []
        self.links: list[str] = []
        self.details_depth = 0
        self.unfolded_figures = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag == 'details':
            self.details_depth += 1
            assert 'open' not in values, 'Details should start collapsed'
        if tag == 'figure' and not self.details_depth:
            self.unfolded_figures += 1
        if values.get('id'):
            self.ids.append(values['id'])
        for name in ('href', 'src'):
            if values.get(name):
                self.links.append(values[name])

    def handle_endtag(self, tag: str) -> None:
        if tag == 'details':
            self.details_depth -= 1
            assert self.details_depth >= 0, 'Unmatched details closing tag'


class IntegratedReportTests(unittest.TestCase):
    def test_page_links_and_current_results(self) -> None:
        source = PAGE.read_text()
        page = PageParser()
        page.feed(source)
        self.assertEqual(page.details_depth, 0)
        self.assertEqual(page.unfolded_figures, 0)
        self.assertEqual(len(page.ids), len(set(page.ids)))
        for link in page.links:
            url = urlsplit(link)
            if url.scheme or url.netloc or url.path.startswith('/'):
                continue
            if url.path:
                self.assertTrue((PAGE.parent / url.path).exists(), link)
            elif url.fragment:
                self.assertIn(url.fragment, page.ids)
        for stale in ('UPDATE START', '18 October update', '276 precinct/control tests', 'Changes from the earlier'):
            self.assertNotIn(stale, source)
        for current in ('47,236', '694', '657', '219', 'Ohio Senate'):
            self.assertIn(current, source)

    def test_builders_preserve_editorial_page(self) -> None:
        for name in ('build_expanded_report.py', 'build_precinct_report.py'):
            tree = ast.parse((ROOT / 'usa-2024/scripts' / name).read_text())
            guards = [node for node in ast.walk(tree) if isinstance(node, ast.If)
                      and 'report-layout' in ast.unparse(node.test)]
            self.assertEqual(len(guards), 1, name)
            # Exercise the actual guard without rerunning the election analysis.
            target = Mock()
            text = PAGE.read_text()
            env = {'page': text if 'expanded' in name else target, 'content': text}
            exec(compile(ast.Module(body=guards, type_ignores=[]), name, 'exec'), env)
            target.write_text.assert_not_called()
            self.assertEqual(env['page'], text if 'expanded' in name else target)


if __name__ == '__main__':
    unittest.main()
