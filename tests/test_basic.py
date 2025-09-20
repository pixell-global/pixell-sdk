"""Basic tests to ensure the package is importable."""


def test_import():
    """Test that the package can be imported."""
    import pixell

    assert pixell is not None


def test_cli_import():
    """Test that CLI can be imported."""
    from pixell.cli.main import cli

    assert cli is not None


def test_version():
    """Test that version is accessible."""
    from pixell.cli.main import __version__

    assert __version__ is not None
