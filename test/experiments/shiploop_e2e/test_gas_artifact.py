"""Tests for the read-only GAS source/resource closure inspector."""
from __future__ import annotations

import os
from pathlib import Path
import socket
import sys
import unittest
from unittest.mock import patch


HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gas_artifact  # noqa: E402


FIXTURES = HERE / "fixtures" / "gas"


def configured_retained_product(variable: str) -> Path | None:
    value = os.environ.get(variable)
    return Path(value).expanduser() if value else None


RETAINED_TTT = configured_retained_product("SHIPLOOP_E2E_RETAINED_TTT")
RETAINED_CHECKERS = configured_retained_product("SHIPLOOP_E2E_RETAINED_CHECKERS")


def issue_codes(result: dict) -> set[str]:
    return {row["code"] for row in result["issues"]}


class GasArtifactTests(unittest.TestCase):
    def inspect(self, fixture: str, entrypoint: str | None = None) -> dict:
        return gas_artifact.inspect_artifact(FIXTURES / fixture, entrypoint)

    def test_literal_template_include_assembles_and_hashes_every_consumed_source(self) -> None:
        result = self.inspect("template_ok")
        self.assertEqual(result["status"], "pass")
        self.assertEqual(result["entrypoint"], {
            "logical_name": "Page", "path": "Page.html", "mode": "template", "selection": "doGet",
            "source_path": "Page.html",
        })
        self.assertIn("window.fixtureReady", result["rendered_html"])
        self.assertNotIn("<?!=", result["rendered_html"])
        self.assertEqual(set(result["source_hashes"]), {"Code.gs", "Page.html", "Styles.html", "Client.html"})
        self.assertEqual(result["official_guidance"], gas_artifact.OFFICIAL_GUIDANCE)

    def test_raw_relative_script_fails_even_when_a_sibling_file_exists(self) -> None:
        result = self.inspect("direct_relative_bad")
        self.assertEqual(result["status"], "fail")
        self.assertIn("relative-resource-without-gas-route", issue_codes(result))
        self.assertTrue((FIXTURES / "direct_relative_bad" / "engine.js").is_file())
        self.assertIn('src="engine.js"', result["rendered_html"])

    def test_css_import_and_url_dependencies_are_not_hidden_by_sibling_assets(self) -> None:
        result = self.inspect("css_relative_bad")
        self.assertEqual(result["status"], "fail")
        self.assertGreaterEqual(
            sum(row["code"] == "relative-resource-without-gas-route" for row in result["issues"]), 2
        )

    def test_https_routes_pass_source_closure_without_contacting_them(self) -> None:
        with patch.object(socket, "create_connection", side_effect=AssertionError("network must not be used")):
            result = self.inspect("external_https")
        self.assertEqual(result["status"], "pass")
        self.assertEqual(len(result["external_resources"]), 3)
        self.assertTrue(all(row["availability"] == "unverified" for row in result["external_resources"]))
        self.assertTrue(all(row["route"] == "https-external" for row in result["external_resources"]))

    def test_dynamic_server_rpc_stays_unverified(self) -> None:
        result = self.inspect("dynamic_rpc")
        self.assertEqual(result["status"], "unverified")
        self.assertIn("dynamic-client-resource-or-rpc", issue_codes(result))

    def test_common_dynamic_loaders_stay_unverified_even_with_a_sibling_dependency(self) -> None:
        result = self.inspect("dynamic_loaders")
        self.assertEqual(result["status"], "unverified")
        self.assertTrue((FIXTURES / "dynamic_loaders" / "engine.js").is_file())
        self.assertTrue({
            "dynamic-fetch-loader",
            "dynamic-xhr-loader",
            "dynamic-import-scripts",
            "dynamic-script-source-assignment",
        }.issubset(issue_codes(result)))

    def test_embedded_documents_fail_for_raw_relative_routes_and_stay_unverified_when_external(self) -> None:
        relative = self.inspect("embedded_relative")
        self.assertEqual(relative["status"], "fail")
        self.assertEqual(
            sum(row["code"] == "relative-embedded-document-without-gas-route" for row in relative["issues"]), 3
        )
        external = self.inspect("embedded_external")
        self.assertEqual(external["status"], "unverified")
        self.assertIn("embedded-document-not-inspected", issue_codes(external))

    def test_dynamic_template_build_stays_unverified_and_http_is_not_a_valid_route(self) -> None:
        dynamic = self.inspect("dynamic_template")
        self.assertEqual(dynamic["status"], "unverified")
        self.assertIn("unresolved-template-scriptlet", issue_codes(dynamic))
        insecure = self.inspect("insecure_http")
        self.assertEqual(insecure["status"], "fail")
        self.assertIn("insecure-external-resource", issue_codes(insecure))

    def test_include_cycle_missing_file_and_unsafe_path_fail_closed(self) -> None:
        cases = {
            "include_cycle": "include-cycle",
            "missing_include": "html-file-missing",
            "unsafe_include": "unsafe-html-name",
        }
        for fixture, expected_code in cases.items():
            with self.subTest(fixture=fixture):
                result = self.inspect(fixture)
                self.assertEqual(result["status"], "fail")
                self.assertIn(expected_code, issue_codes(result))
                self.assertNotIn("rendered_html", result)

    def test_static_doget_cannot_be_overridden_to_choose_a_benign_unused_page(self) -> None:
        result = self.inspect("benign_unused", "Good")
        self.assertEqual(result["status"], "fail")
        self.assertEqual(result["entrypoint"]["logical_name"], "Bad")
        self.assertIn("relative-resource-without-gas-route", issue_codes(result))
        self.assertIn("entrypoint-argument-ignored", {row["code"] for row in result["limitations"]})

    def test_explicit_self_contained_page_is_supported_when_no_doget_exists(self) -> None:
        result = self.inspect("self_contained", "Page.html")
        self.assertEqual(result["status"], "pass")
        self.assertEqual(result["entrypoint"]["selection"], "argument")
        self.assertIn("window.ok", result["rendered_html"])
        missing = self.inspect("self_contained")
        self.assertEqual(missing["status"], "unverified")
        self.assertIn("entrypoint-not-found", issue_codes(missing))

    @unittest.skipUnless(
        RETAINED_TTT is not None and RETAINED_TTT.is_dir()
        and RETAINED_CHECKERS is not None and RETAINED_CHECKERS.is_dir(),
        "retained-product checks are opt-in; set SHIPLOOP_E2E_RETAINED_TTT and "
        "SHIPLOOP_E2E_RETAINED_CHECKERS to product directories",
    )
    def test_retained_tictactoe_passes_and_checkers_fails_the_actual_served_entrypoint(self) -> None:
        assert RETAINED_TTT is not None
        assert RETAINED_CHECKERS is not None
        ttt = gas_artifact.inspect_artifact(RETAINED_TTT)
        checkers = gas_artifact.inspect_artifact(RETAINED_CHECKERS)
        self.assertEqual(ttt["status"], "pass")
        self.assertEqual(ttt["entrypoint"]["logical_name"], "Index")
        self.assertIn("JavaScript.html", ttt["source_hashes"])
        self.assertIn("TicTacToe.create", ttt["rendered_html"])
        self.assertEqual(checkers["status"], "fail")
        self.assertEqual(checkers["entrypoint"]["logical_name"], "Index")
        self.assertIn("relative-resource-without-gas-route", issue_codes(checkers))
        self.assertIn('src="engine.js"', checkers["rendered_html"])


if __name__ == "__main__":
    unittest.main()
