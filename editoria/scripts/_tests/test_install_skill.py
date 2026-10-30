"""Tests for the portable, non-destructive EditorIA skill installer."""

import os
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from install_skill import install, InstallError


class InstallSkillTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="editoria_install_")
        self.addCleanup(self.temp.cleanup)
        self.source = os.path.join(self.temp.name, "source", "editoria")
        os.makedirs(self.source)
        with open(os.path.join(self.source, "SKILL.md"), "w", encoding="utf-8") as f:
            f.write("---\nname: editoria\n---\n")
        self.destination = os.path.join(self.temp.name, "skills", "editoria")

    def test_creates_link_and_is_idempotent(self):
        install(self.source, self.destination)
        self.assertTrue(os.path.islink(self.destination))
        self.assertEqual(os.path.realpath(self.destination), os.path.realpath(self.source))
        self.assertEqual(install(self.source, self.destination), "already-installed")

    def test_existing_user_directory_is_preserved_and_refused(self):
        os.makedirs(self.destination)
        custom = os.path.join(self.destination, "custom.md")
        with open(custom, "w", encoding="utf-8") as f:
            f.write("user data")
        with self.assertRaises(InstallError):
            install(self.source, self.destination)
        with open(custom, encoding="utf-8") as f:
            self.assertEqual(f.read(), "user data")

    def test_broken_symlink_requires_explicit_repair_then_points_to_source(self):
        os.makedirs(os.path.dirname(self.destination))
        os.symlink(os.path.join(self.temp.name, "old", "SKILL"), self.destination)
        with self.assertRaises(InstallError):
            install(self.source, self.destination)
        self.assertTrue(os.path.islink(self.destination))
        install(self.source, self.destination, repair_broken_link=True)
        self.assertEqual(os.path.realpath(self.destination), os.path.realpath(self.source))

    def test_unrelated_symlink_is_never_replaced(self):
        other = os.path.join(self.temp.name, "other")
        os.mkdir(other)
        os.makedirs(os.path.dirname(self.destination))
        os.symlink(other, self.destination)
        with self.assertRaises(InstallError):
            install(self.source, self.destination, repair_broken_link=True)
        self.assertEqual(os.path.realpath(self.destination), os.path.realpath(other))

    def test_copy_mode_refuses_existing_destination(self):
        os.makedirs(self.destination)
        with self.assertRaises(InstallError):
            install(self.source, self.destination, copy=True)

    def test_copy_mode_installs_a_portable_copy(self):
        self.assertEqual(install(self.source, self.destination, copy=True), "installed-copy")
        self.assertFalse(os.path.islink(self.destination))
        with open(os.path.join(self.destination, "SKILL.md"), encoding="utf-8") as f:
            self.assertIn("name: editoria", f.read())

    def test_copy_failure_does_not_delete_concurrently_created_destination(self):
        marker = os.path.join(self.destination, "created-by-another-process.txt")

        def concurrent_copy(_source, _staging_destination, **_kwargs):
            os.makedirs(self.destination)
            with open(marker, "w", encoding="utf-8") as f:
                f.write("other process owns this directory")
            raise FileExistsError(self.destination)

        with mock.patch("install_skill.shutil.copytree", side_effect=concurrent_copy):
            with self.assertRaises(InstallError):
                install(self.source, self.destination, copy=True)
        with open(marker, encoding="utf-8") as f:
            self.assertEqual(f.read(), "other process owns this directory")


if __name__ == "__main__":
    unittest.main()
