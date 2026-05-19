"""Integration-style tests for app wiring and backend loading."""
from __future__ import annotations

import os
import tempfile
import unittest

import app as wikifish_app
from dump_compiler import compile_dump_snapshot
from main import load_backend
from tests.test_support import write_fixture_dump_dir


class AppAndMainTests(unittest.TestCase):
    """Smoke tests around app wiring and runtime backend loading."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        dump_dir = write_fixture_dump_dir(self.temp_dir.name)
        self.output_dir = os.path.join(self.temp_dir.name, 'compiled')
        compile_dump_snapshot(dump_dir, self.output_dir)
        self.backend = load_backend(self.output_dir)

    def tearDown(self) -> None:
        close = getattr(self.backend, 'close', None)
        if callable(close):
            close()
        self.temp_dir.cleanup()

    def test_load_backend_prefers_compiled_snapshot(self) -> None:
        snapshot = self.backend.snapshot_info()
        self.assertEqual(snapshot.snapshot_date, '2026-05-01')
        self.assertEqual(snapshot.article_count, 4)

    def test_app_callback_canonicalises_titles_and_shows_snapshot_notice(self) -> None:
        wikifish_app.configure_backend(self.backend)

        store, error, style = wikifish_app.run(1, 'Redirect_Alpha\nCharlie', 'bfs', 3)

        self.assertEqual(error, '')
        self.assertEqual(style, {'display': 'block'})
        self.assertEqual(store['player_path'], ['Alpha', 'Charlie'])
        self.assertIn('2026-05-01', wikifish_app.startup_notice_text)


if __name__ == '__main__':
    unittest.main()
