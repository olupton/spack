# Copyright 2013-2021 Lawrence Livermore National Security, LLC and other
# Spack Project Developers. See the top-level COPYRIGHT file for details.
#
# SPDX-License-Identifier: (Apache-2.0 OR MIT)

import os
import shutil
import sys

import pytest

from llnl.util.filesystem import FileFilter

import spack.main
import spack.paths
import spack.repo
from spack.cmd.style import changed_files
from spack.util.executable import which

style = spack.main.SpackCommand("style")

# spack style requires git to run -- skip the tests if it's not there
pytestmark = pytest.mark.skipif(not which('git'), reason='requires git')

# The style tools have requirements to use newer Python versions.  We simplify by
# requiring Python 3.6 or higher to run spack style.
skip_old_python = pytest.mark.skipif(
    sys.version_info < (3, 6), reason='requires Python 3.6 or higher')


@pytest.fixture(scope="function")
def flake8_package():
    """Style only checks files that have been modified. This fixture makes a small
    change to the ``flake8`` mock package, yields the filename, then undoes the
    change on cleanup.
    """
    repo = spack.repo.Repo(spack.paths.mock_packages_path)
    filename = repo.filename_for_package_name("flake8")
    tmp = filename + ".tmp"

    try:
        shutil.copy(filename, tmp)
        package = FileFilter(filename)
        package.filter("state = 'unmodified'", "state = 'modified'", string=True)
        yield filename
    finally:
        shutil.move(tmp, filename)


@pytest.fixture
def flake8_package_with_errors(scope="function"):
    """A flake8 package with errors."""
    repo = spack.repo.Repo(spack.paths.mock_packages_path)
    filename = repo.filename_for_package_name("flake8")
    tmp = filename + ".tmp"

    try:
        shutil.copy(filename, tmp)
        package = FileFilter(filename)
        package.filter("state = 'unmodified'", "state    =    'modified'", string=True)
        package.filter(
            "from spack import *", "from spack import *\nimport os", string=True
        )
        yield filename
    finally:
        shutil.move(tmp, filename)


def test_changed_files(flake8_package):
    # changed_files returns file paths relative to the root
    # directory of Spack. Convert to absolute file paths.
    files = [os.path.join(spack.paths.prefix, path) for path in changed_files()]

    # There will likely be other files that have changed
    # when these tests are run
    assert flake8_package in files


def test_changed_no_base(tmpdir, capfd):
    """Ensure that we fail gracefully with no base branch."""
    tmpdir.join("bin").ensure("spack")
    git = which("git", required=True)
    with tmpdir.as_cwd():
        git("init")
        git("config", "user.name", "test user")
        git("config", "user.email", "test@user.com")
        git("add", ".")
        git("commit", "-m", "initial commit")

        with pytest.raises(SystemExit):
            changed_files(base="foobar")

        out, err = capfd.readouterr()
        assert "This repository does not have a 'foobar' branch." in err


def test_changed_files_all_files(flake8_package):
    # it's hard to guarantee "all files", so do some sanity checks.
    files = set([
        os.path.join(spack.paths.prefix, path)
        for path in changed_files(all_files=True)
    ])

    # spack has a lot of files -- check that we're in the right ballpark
    assert len(files) > 6000

    # a builtin package
    zlib = spack.repo.path.get_pkg_class("zlib")
    assert zlib.module.__file__ in files

    # a core spack file
    assert os.path.join(spack.paths.module_path, "spec.py") in files

    # a mock package
    assert flake8_package in files

    # this test
    assert __file__ in files

    # ensure externals are excluded
    assert not any(f.startswith(spack.paths.external_path) for f in files)


@pytest.mark.skipif(sys.version_info >= (3, 6), reason="doesn't apply to newer python")
def test_fail_on_old_python():
    """Ensure that `spack style` runs but fails with older python."""
    style(fail_on_error=False)
    assert style.returncode != 0


@skip_old_python
@pytest.mark.skipif(not which("flake8"), reason="flake8 is not installed.")
@pytest.mark.skipif(not which("isort"), reason="isort is not installed.")
@pytest.mark.skipif(not which("mypy"), reason="mypy is not installed.")
@pytest.mark.skipif(not which("black"), reason="black is not installed.")
def test_external_root(flake8_package_with_errors, tmpdir):
    """Ensure we can run in a separate root directory w/o configuration files."""
    git = which("git", required=True)
    with tmpdir.as_cwd():
        git

    # create a sort-of spack-looking directory
    script = tmpdir / "bin" / "spack"
    script.ensure()
    spack_dir = tmpdir / "lib" / "spack" / "spack"
    spack_dir.ensure("__init__.py")
    llnl_dir = tmpdir / "lib" / "spack" / "llnl"
    llnl_dir.ensure("__init__.py")

    # create a base develop branch
    with tmpdir.as_cwd():
        git("init")
        git("config", "user.name", "test user")
        git("config", "user.email", "test@user.com")
        git("add", ".")
        git("commit", "-m", "initial commit")
        git("branch", "-m", "develop")
        git("checkout", "-b", "feature")

    # copy the buggy package in
    py_file = spack_dir / "dummy.py"
    py_file.ensure()
    shutil.copy(flake8_package_with_errors, str(py_file))

    # add the buggy file on the feature branch
    with tmpdir.as_cwd():
        git("add", str(py_file))
        git("commit", "-m", "add new file")

    # make sure tools are finding issues with external root,
    # not the real one.
    output = style(
        "--root-relative", "--black", "--root", str(tmpdir),
        fail_on_error=False
    )

    # make sure it failed
    assert style.returncode != 0

    # isort error
    assert "%s Imports are incorrectly sorted" % str(py_file) in output

    # mypy error
    assert 'lib/spack/spack/dummy.py:10: error: Name "Package" is not defined' in output

    # black error
    assert "--- lib/spack/spack/dummy.py" in output
    assert "+++ lib/spack/spack/dummy.py" in output

    # flake8 error
    assert "lib/spack/spack/dummy.py:7: [F401] 'os' imported but unused" in output


@skip_old_python
@pytest.mark.skipif(not which("flake8"), reason="flake8 is not installed.")
def test_style(flake8_package, tmpdir):
    root_relative = os.path.relpath(flake8_package, spack.paths.prefix)

    # use a working directory to test cwd-relative paths, as tests run in
    # the spack prefix by default
    with tmpdir.as_cwd():
        relative = os.path.relpath(flake8_package)

        # no args
        output = style()
        assert relative in output
        assert "spack style checks were clean" in output

        # one specific arg
        output = style(flake8_package)
        assert relative in output
        assert "spack style checks were clean" in output

        # specific file that isn't changed
        output = style(__file__)
        assert relative not in output
        assert __file__ in output
        assert "spack style checks were clean" in output

    # root-relative paths
    output = style("--root-relative", flake8_package)
    assert root_relative in output
    assert "spack style checks were clean" in output


@skip_old_python
@pytest.mark.skipif(not which("flake8"), reason="flake8 is not installed.")
def test_style_with_errors(flake8_package_with_errors):
    root_relative = os.path.relpath(flake8_package_with_errors, spack.paths.prefix)
    output = style("--root-relative", flake8_package_with_errors, fail_on_error=False)
    assert root_relative in output
    assert style.returncode != 0
    assert "spack style found errors" in output


@skip_old_python
@pytest.mark.skipif(not which("flake8"), reason="flake8 is not installed.")
@pytest.mark.skipif(not which("black"), reason="black is not installed.")
def test_style_with_black(flake8_package_with_errors):
    output = style("--black", flake8_package_with_errors, fail_on_error=False)
    assert "black found errors" in output
    assert style.returncode != 0
    assert "spack style found errors" in output
