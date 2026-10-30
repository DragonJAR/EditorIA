#!/usr/bin/env python3
"""Install or link the EditorIA skill without replacing user data.

Examples:
    python3 editoria/scripts/install_skill.py --destination ~/.claude/skills/editoria
    python3 editoria/scripts/install_skill.py --destination /path/to/skills/editoria --copy
    python3 editoria/scripts/install_skill.py --destination /path/to/skills/editoria --repair-broken-link
"""

import argparse
import os
import shutil
import sys
import tempfile


class InstallError(Exception):
    """A safe installation could not be completed."""


def install(source, destination, *, copy=False, repair_broken_link=False):
    """Install source at destination; existing user content is never overwritten."""
    source = os.path.abspath(os.path.expanduser(source))
    destination = os.path.abspath(os.path.expanduser(destination))
    skill_file = os.path.join(source, "SKILL.md")
    if not os.path.isfile(skill_file):
        raise InstallError(f"Source is not an EditorIA skill directory: {source} (SKILL.md missing)")
    try:
        destination_is_nested = os.path.commonpath([source, destination]) == source
    except ValueError:
        destination_is_nested = False  # e.g. different Windows drive letters
    if destination_is_nested:
        raise InstallError("Destination cannot be inside the source skill directory.")

    if os.path.lexists(destination):
        if os.path.islink(destination):
            current = os.path.realpath(destination)
            if current == os.path.realpath(source):
                return "already-installed"
            if not os.path.exists(destination):
                if not repair_broken_link:
                    raise InstallError(
                        f"Destination is a broken symlink: {destination}. "
                        "Inspect it, then rerun with --repair-broken-link to replace that link."
                    )
                os.unlink(destination)
            else:
                raise InstallError(
                    f"Destination is an existing symlink to another location: {destination}. "
                    "It was not changed; inspect or move it manually."
                )
        else:
            raise InstallError(
                f"Destination already exists and may contain user data: {destination}. "
                "It was not changed; choose another path or move it manually."
            )

    os.makedirs(os.path.dirname(destination), exist_ok=True)
    try:
        if copy:
            staging_parent = tempfile.mkdtemp(
                prefix=".editoria-install-", dir=os.path.dirname(destination))
            staged_destination = os.path.join(staging_parent, "editoria")
            try:
                shutil.copytree(source, staged_destination, symlinks=True,
                                ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache", ".ruff_cache"))
                if os.path.lexists(destination):
                    raise InstallError(
                        f"Destination appeared during installation: {destination}. "
                        "It was not changed; the staged copy was discarded."
                    )
                os.rename(staged_destination, destination)
            finally:
                # This path was created by this invocation; never clean the destination.
                shutil.rmtree(staging_parent, ignore_errors=True)
            return "installed-copy"
        os.symlink(source, destination, target_is_directory=True)
        return "installed-link"
    except OSError as exc:
        raise InstallError(
            f"Could not install EditorIA at {destination}: {exc}. "
            + ("On Windows, enable symlink support or retry with --copy." if not copy
               else "Check destination permissions and available disk space.")
        ) from exc


def main(argv=None):
    parser = argparse.ArgumentParser(description="Install EditorIA without overwriting existing files.")
    parser.add_argument("--destination", required=True,
                        help="exact target path, normally a skill directory named 'editoria'")
    parser.add_argument("--copy", action="store_true",
                        help="copy files instead of creating a symlink (destination must not exist)")
    parser.add_argument("--repair-broken-link", action="store_true",
                        help="replace only a broken symlink at the selected destination")
    args = parser.parse_args(argv)
    source = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    try:
        outcome = install(source, args.destination, copy=args.copy,
                          repair_broken_link=args.repair_broken_link)
    except (InstallError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(f"EditorIA {outcome}: {os.path.abspath(os.path.expanduser(args.destination))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
