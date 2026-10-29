"""
Guards for the gettext catalogs in locale/.

A merge of develop2 (2026-06-19) left locale/fr/LC_MESSAGES/django.po with
duplicate entries: msgfmt refused it, the committed .mo silently stopped
following the .po, and new translations never reached the site. These tests
fail as soon as a .po does not compile or the committed .mo is out of sync.
"""

import gettext
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase

LOCALE_DIR = Path(settings.BASE_DIR) / "locale"
CATALOGS = sorted(LOCALE_DIR.glob("*/LC_MESSAGES/django.po"))


@unittest.skipUnless(shutil.which("msgfmt"), "GNU gettext (msgfmt) is not installed")
class TranslationCatalogTest(SimpleTestCase):
    def _compile(self, po_path):
        """Compile like `compilemessages` does; return (returncode, stderr, catalog)."""
        with tempfile.TemporaryDirectory() as tmp:
            mo_path = Path(tmp) / "django.mo"
            result = subprocess.run(
                ["msgfmt", "--check-format", "-o", str(mo_path), str(po_path)],
                capture_output=True, text=True,
            )
            catalog = None
            if result.returncode == 0:
                with open(mo_path, "rb") as mo:
                    catalog = gettext.GNUTranslations(mo)._catalog
            return result.returncode, result.stderr, catalog

    def test_there_is_at_least_one_catalog(self):
        self.assertTrue(CATALOGS, "no locale/*/LC_MESSAGES/django.po found")

    def test_every_po_compiles(self):
        for po_path in CATALOGS:
            with self.subTest(catalog=str(po_path.relative_to(LOCALE_DIR))):
                returncode, stderr, _ = self._compile(po_path)
                errors = "\n".join(
                    line for line in stderr.splitlines() if "header field" not in line
                )
                self.assertEqual(returncode, 0, errors)

    def test_committed_mo_matches_po(self):
        for po_path in CATALOGS:
            with self.subTest(catalog=str(po_path.relative_to(LOCALE_DIR))):
                _, _, expected = self._compile(po_path)
                if expected is None:
                    self.skipTest("the .po does not compile (see test_every_po_compiles)")
                with open(po_path.with_suffix(".mo"), "rb") as mo:
                    committed = gettext.GNUTranslations(mo)._catalog
                stale = sorted(
                    str(k) for k in set(expected) | set(committed)
                    if expected.get(k) != committed.get(k)
                )
                self.assertFalse(
                    stale,
                    "django.mo is out of sync with django.po for %d message(s), "
                    "e.g. %s — run `python manage.py compilemessages --ignore venv`"
                    % (len(stale), stale[:5]),
                )
