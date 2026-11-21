import sys
import unittest
import uuid
from pathlib import Path
from unittest import mock


WEB_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WEB_DIR))

import learning_service
import linux_runtime


class LinuxRuntimeTests(unittest.TestCase):
    def test_linux_content_matches_the_fixed_runtime_allowlist(self):
        course = next(
            item for item in learning_service.content()["courses"]
            if item["id"] == "linux"
        )
        content_ids = {
            module[key]["id"]
            for module in course["modules"]
            for key in ("guided_practice", "independent_practice")
        }
        self.assertEqual(content_ids, linux_runtime.exercise_ids())

    def test_unallowlisted_exercise_is_rejected_before_starting_wsl(self):
        with mock.patch.object(linux_runtime, "_invoke_wsl") as invoke:
            with self.assertRaises(linux_runtime.LinuxRuntimeError):
                linux_runtime.run_exercise(str(uuid.uuid4()), "echo arbitrary-command")
        invoke.assert_not_called()

    def test_workspace_rejects_traversal_and_invalid_learner_ids(self):
        with self.assertRaises(linux_runtime.LinuxRuntimeError):
            linux_runtime._workspace_path(str(uuid.uuid4()), "../outside")
        with self.assertRaises(linux_runtime.LinuxRuntimeError):
            linux_runtime._workspace_path("not-a-uuid", "linux-paths-guided")

    def test_wsl_list_parser_requires_the_distro_version_field(self):
        output = (
            "  NAME            STATE           VERSION\r\n"
            "* Ubuntu          Running         2\r\n"
            "  Debian          Stopped         1\r\n"
        )
        self.assertEqual(linux_runtime._parse_wsl_list(output), {"ubuntu": 2, "debian": 1})

    def test_check_status_accepts_versioned_ubuntu_distribution_name(self):
        list_output = (
            "  NAME            STATE           VERSION\r\n"
            "* Ubuntu-24.04    Running         2\r\n"
        )
        with (
            mock.patch.object(linux_runtime.os, "name", "nt"),
            mock.patch.object(
                linux_runtime,
                "_invoke_wsl",
                side_effect=[
                    (0, list_output, ""),
                ],
            ),
            mock.patch.object(
                linux_runtime,
                "_wsl_command",
                side_effect=[
                    (0, "1000", ""),
                    (0, "/home/alumno", ""),
                    (0, "", ""),
                    (0, "6.18.58.1-microsoft-standard-WSL2", ""),
                ],
            ),
        ):
            result = linux_runtime._check_status()
        self.assertTrue(result["available"])
        self.assertEqual(result["distribution"], "Ubuntu-24.04")

    def test_wsl_help_output_is_summarized_as_an_update_requirement(self):
        help_output = (
            "Copyright (c) Microsoft Corporation.\n"
            "Usage: wsl.exe [Argument]\n"
            + ("--install options and examples\n" * 100)
        )
        with (
            mock.patch.object(linux_runtime.os, "name", "nt"),
            mock.patch.object(
                linux_runtime,
                "_invoke_wsl",
                return_value=(1, help_output, ""),
            ),
        ):
            result = linux_runtime._check_status()
        self.assertFalse(result["available"])
        self.assertIn("Actualiza WSL", result["reason"])
        self.assertLess(len(result["reason"]), 200)
        self.assertNotIn("Copyright", result["reason"])

    def test_project_analysis_parses_only_ids_from_actual_command_output(self):
        output = (
            "ERROR_IDS_BEGIN\nPX-510\nPX-513\n"
            "PENDING_IDS_BEGIN\nPX-511\n__ACADEMY_CHECK_OK__\n"
        )
        with (
            mock.patch.object(
                linux_runtime,
                "status",
                return_value={
                    "available": True,
                    "distribution": "Ubuntu",
                    "wsl_version": 2,
                    "kernel": "test-kernel",
                    "home": "/home/test",
                },
            ),
            mock.patch.object(linux_runtime, "_prepare_workspace", return_value="$HOME/test"),
            mock.patch.object(
                linux_runtime,
                "_run_script",
                return_value={
                    "passed": True,
                    "returncode": 0,
                    "stdout": output,
                    "stderr": "",
                    "runtime": "test-kernel",
                },
            ),
        ):
            result = linux_runtime.run_project_analysis(str(uuid.uuid4()))
        self.assertTrue(result["passed"])
        self.assertEqual(result["error_ids"], ["PX-510", "PX-513"])
        self.assertEqual(result["pending_ids"], ["PX-511"])
        self.assertIn("grep level=ERROR", result["commands"])


if __name__ == "__main__":
    unittest.main()
