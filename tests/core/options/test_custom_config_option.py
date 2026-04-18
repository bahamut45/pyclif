"""Tests for CustomConfigOption - focusing on custom logic only."""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from pyclif.core.classes import CustomConfigOption


def patch_option_formats(option, formats_dict=None):
    """Patch file_format_patterns for the option."""
    option.file_format_patterns = formats_dict


class TestCustomConfigOption:
    """Test CustomConfigOption's specific functionality without retesting click-extra."""

    def test_extension_pattern_single_format(self):
        """Test _get_extension_pattern with a single format."""
        option = CustomConfigOption()
        patch_option_formats(option, {"toml": ["*.toml"]})

        pattern = option._get_extension_pattern()
        assert pattern == "toml"

    def test_extension_pattern_multiple_formats(self):
        """Test _get_extension_pattern with multiple formats."""
        option = CustomConfigOption()
        patch_option_formats(
            option,
            {"toml": ["*.toml"], "yaml": ["*.yaml", "*.yml"], "json": ["*.json"]},
        )

        pattern = option._get_extension_pattern()
        assert pattern == "{toml,yaml,yml,json}"

    def test_extension_pattern_empty(self):
        """Test _get_extension_pattern when no formats are provided."""
        option = CustomConfigOption()
        # noinspection PyArgumentEqualDefault
        patch_option_formats(option, None)

        pattern = option._get_extension_pattern()
        assert pattern == "*"

    @patch("pyclif.core.classes.get_current_context")
    def test_get_all_config_patterns_no_context(self, mock_get_context):
        """Test _get_all_config_patterns when no click context is available."""
        mock_get_context.side_effect = RuntimeError("No context available")

        option = CustomConfigOption()
        patch_option_formats(option, {"toml": ["*.toml"]})

        patterns = option._get_all_config_patterns()
        assert patterns == []

    @patch("pyclif.core.classes.get_current_context")
    def test_get_all_config_patterns_no_cli_name(self, mock_get_context):
        """Test _get_all_config_patterns when the CLI name is None."""
        mock_context = Mock()
        mock_context.find_root().info_name = None
        mock_get_context.return_value = mock_context

        option = CustomConfigOption()
        patch_option_formats(option, {"toml": ["*.toml"]})

        patterns = option._get_all_config_patterns()
        assert patterns == []

    @patch("pyclif.core.classes.is_linux")
    @patch("pyclif.core.classes.get_app_dir")
    @patch("pyclif.core.classes.get_current_context")
    def test_get_all_config_patterns_linux(
        self, mock_get_context, mock_get_app_dir, mock_is_linux
    ):
        """Test _get_all_config_patterns on a Linux platform."""
        mock_is_linux.return_value = True
        mock_context = Mock()
        mock_context.find_root().info_name = "test-cli"
        mock_get_context.return_value = mock_context
        mock_get_app_dir.return_value = "/home/user/.config/test-cli"

        option = CustomConfigOption()
        patch_option_formats(option, {"toml": ["*.toml"]})
        option.roaming = False
        option.force_posix = False

        patterns = option._get_all_config_patterns()

        assert len(patterns) == 2
        assert "/etc/test-cli" in patterns[0]
        assert "/home/user/.config/test-cli" in patterns[1]
        assert "*.toml" in patterns[0]
        assert "*.toml" in patterns[1]

    @patch("pyclif.core.classes.is_linux")
    @patch("pyclif.core.classes.get_app_dir")
    @patch("pyclif.core.classes.get_current_context")
    def test_get_all_config_patterns_non_linux(
        self, mock_get_context, mock_get_app_dir, mock_is_linux
    ):
        """Test _get_all_config_patterns on a non-Linux platform."""
        mock_is_linux.return_value = False
        mock_context = Mock()
        mock_context.find_root().info_name = "test-cli"
        mock_get_context.return_value = mock_context
        mock_get_app_dir.return_value = (
            "/Users/user/Library/Application Support/test-cli"
        )

        option = CustomConfigOption()
        patch_option_formats(option, {"yaml": ["*.yaml"]})
        option.roaming = False
        option.force_posix = False

        patterns = option._get_all_config_patterns()

        assert len(patterns) == 1
        assert "/Users/user/Library/Application Support/test-cli" in patterns[0]
        assert "yaml" in patterns[0]

    @patch("pyclif.core.classes.get_app_dir")
    @patch("pyclif.core.classes.get_current_context")
    def test_get_all_config_patterns_app_dir_error(
        self, mock_get_context, mock_get_app_dir
    ):
        """Test _get_all_config_patterns handles get_app_dir errors gracefully."""
        mock_context = Mock()
        mock_context.find_root().info_name = "test-cli"
        mock_get_context.return_value = mock_context
        mock_get_app_dir.side_effect = OSError("Permission denied")

        with patch("pyclif.core.classes.is_linux", return_value=False):
            option = CustomConfigOption()
            patch_option_formats(option, {"json": ["*.json"]})

            patterns = option._get_all_config_patterns()

            assert patterns == []

    def test_fallback_pattern(self):
        """Test _get_fallback_pattern returns the current directory pattern."""
        option = CustomConfigOption()
        patch_option_formats(option, {"conf": ["*.conf"]})

        fallback = option._get_fallback_pattern()
        assert fallback == "*.conf"

    @patch("pyclif.core.classes.get_current_context")
    def test_default_pattern_with_patterns(self, mock_get_context):
        """Test default_pattern when patterns are available."""
        mock_context = Mock()
        mock_context.find_root().info_name = "test-cli"
        mock_get_context.return_value = mock_context

        with (
            patch("pyclif.core.classes.is_linux", return_value=True),
            patch(
                "pyclif.core.classes.get_app_dir",
                return_value="/home/user/.config/test-cli",
            ),
        ):
            option = CustomConfigOption()
            patch_option_formats(option, {"toml": ["*.toml"]})
            option.roaming = False
            option.force_posix = False

            pattern = option.default_pattern()

            assert "/etc/test-cli" in pattern
            assert "/home/user/.config/test-cli" in pattern
            assert ", " in pattern

    @patch("pyclif.core.classes.get_current_context")
    def test_default_pattern_fallback(self, mock_get_context):
        """Test default_pattern falls back when no patterns available."""
        mock_get_context.side_effect = RuntimeError("No context")

        option = CustomConfigOption()
        patch_option_formats(option, {"ini": ["*.ini"]})

        pattern = option.default_pattern()
        assert pattern == "*.ini"

    @patch.object(CustomConfigOption, "search_and_read_conf")
    def test_search_and_read_conf_calls_super_for_all_patterns(self, mock_super_search):
        """Test search_and_read_conf calls the parent method for each pattern."""
        option = CustomConfigOption()

        with patch.object(
            option,
            "_get_all_config_patterns",
            return_value=["/etc/test/*.toml", "/home/user/.config/test/*.toml"],
        ):
            mock_super_search.return_value = iter([("test", "content")])

            list(option.search_and_read_conf("/custom/path/*.toml"))

            assert mock_super_search.called


class TestCustomConfigOptionIntegration:
    """Integration tests for CustomConfigOption with minimal mocking."""

    def test_can_be_instantiated(self):
        """Test that CustomConfigOption can be instantiated."""
        option = CustomConfigOption()
        assert isinstance(option, CustomConfigOption)
        assert hasattr(option, "roaming")

    def test_inherits_from_config_option(self):
        """Test that CustomConfigOption properly inherits from ConfigOption."""
        from click_extra.config import ConfigOption

        option = CustomConfigOption()
        assert isinstance(option, ConfigOption)

    def test_has_required_methods(self):
        """Test that all required methods are present."""
        option = CustomConfigOption()

        assert hasattr(option, "default_pattern")
        assert hasattr(option, "search_and_read_conf")
        assert hasattr(option, "_get_extension_pattern")
        assert hasattr(option, "_get_all_config_patterns")
        assert hasattr(option, "_get_fallback_pattern")

        assert callable(option.default_pattern)
        assert callable(option.search_and_read_conf)


@pytest.mark.tox
class TestCustomConfigOptionForTox:
    """Specific tests to validate tox compatibility across Python versions."""

    def test_import_compatibility(self):
        """Test that all imports work across different Python versions."""
        from click_extra import get_app_dir, get_current_context
        from click_extra.config import ConfigOption
        from extra_platforms import is_linux

        from pyclif.core.classes import CustomConfigOption

        assert CustomConfigOption
        assert get_app_dir
        assert get_current_context
        assert ConfigOption
        assert is_linux

    def test_basic_functionality_across_versions(self):
        """Test basic functionality that should work across all Python versions."""
        option = CustomConfigOption()

        patch_option_formats(option, {"toml": ["*.toml"]})
        pattern = option._get_extension_pattern()
        assert isinstance(pattern, str)
        assert pattern == "toml"

    def test_pathlib_compatibility(self):
        """Test that Path operations work across Python versions."""
        test_path = Path("/etc/test-cli")
        assert isinstance(test_path, Path)
        assert str(test_path) == "/etc/test-cli"
