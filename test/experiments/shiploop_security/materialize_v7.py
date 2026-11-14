#!/usr/bin/env python3
"""Assemble the opt-in V7 apparatus from the exact frozen V5 retry and unchanged V6 recipe."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True
from v7 import probe_overlay, registration
from v7.report_context import _rename_new, fresh_output, json_bytes, private_file

HERE = Path(__file__).resolve().parent
V6_OVERLAY = "e5f9b142b34071a56e2cb1fc9fea5586b19e42bfe8cfd622530771e5b0ed04ef"
V6_RECIPE_SHA256 = {
    "materialize.py": "fece1952d303fa5d11b74cd55b0d70dba8409d68c65d3091300c874225622931",
    "scope_evidence.py": "45d41324482a07ff28c5aca524214c1021f842d4fcf71fafaec02b93ec4376ca",
    "controls.py": "4cf1360b83a68c00b16ec2562f026d3b2ec04a806864aacac305d1e88d089bc6",
    "logger_failure.cjs": "b5be20cad9ca5c63016114a328543557849a608d94832bbf87162da61a51ccfe",
    "v6.patch": V6_OVERLAY,
}
# Actual final source bytes reviewed for the port. The old materialization
# receipt predates these changes. None of these paths is loaded at build time.
PORT_SOURCE_SHA256 = {
    "experiment/apparatus/operator/runner.py": "d30a2ba5ffa7ceb9de071ee47900aa270852aad0426ddc2cfa0fc358bf5b19f9",
    "experiment/apparatus/coordination/dispatch.py": "718357504162698618092bf97a633486f575e4e482d78759a0780e39a5bec977",
    "experiment/apparatus/analysis/grade.py": "cc1ee00c611907e084f45042eb020108ff189c143baf1f0c79a14f42d5573916",
    "experiment/apparatus/analysis/decision.py": "615128f5f8afb54e0f75bf6e2b14deb7cda55caea01098fb369b0995483e854b",
    "experiment/apparatus/telemetry.py": "6eb412dab02439fcd0f243ece21efa5b509fda8c71b1ce3962eae52bd621e949",
    "experiment/test_telemetry_v2.py": "4db89b7247daf5739b0b968722c76428326ab32e4c3befe6db6582a5ac8bac44",
    "poststudy-review/build_context.py": "85436c383aafe6e723650b633073108ca0abb6e6c92a0e8cdcca51de67a650ac",
}
SUPPORT = ("auth_cleanup.py", "collector_smoke.py", "git_context.py", "registration.py",
           "report_context.py", "telemetry.py")


def verify_port_sources(completion):
    """Optional read-only provenance check; historical source never executes."""
    completion = Path(completion).absolute()
    for relative, expected in PORT_SOURCE_SHA256.items():
        source = completion / relative
        if (source != source.resolve() or not source.is_file()
                or hashlib.sha256(source.read_bytes()).hexdigest() != expected):
            raise ValueError("pinned completion port source differs: " + relative)
    return dict(PORT_SOURCE_SHA256)


def materialize(source, output):
    source = Path(source).absolute()
    output = fresh_output(output, inputs=(source, HERE.parents[2]))
    if source != source.resolve(strict=True):
        raise ValueError("frozen source is not canonical")
    if any(hashlib.sha256((HERE / name).read_bytes()).hexdigest() != digest
           for name, digest in V6_RECIPE_SHA256.items()):
        raise ValueError("unchanged V6 recipe identity differs")
    stage = Path(tempfile.mkdtemp(prefix=".v7-materialize-", dir=output.parent))
    root = stage / "apparatus"
    env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    env.update(GIT_CEILING_DIRECTORIES=str(stage), GIT_CONFIG_GLOBAL=os.devnull,
               GIT_CONFIG_NOSYSTEM="1", PYTHONDONTWRITEBYTECODE="1")
    subprocess.run([sys.executable, "-B", str(HERE / "materialize.py"), "--frozen", str(source),
                    "--output", str(root)], env=env, umask=0o022, check=True, stdout=subprocess.DEVNULL)
    patch = HERE / "v7.patch"
    for opts in (["--check"], []):
        subprocess.run(["git", "-C", str(root), "apply", "--no-index", "--whitespace=nowarn", "--unidiff-zero",
                        *opts, str(patch)], env=env, umask=0o022, check=True)
    probes = probe_overlay.apply(root)
    for row in probes["files"]:
        if row["before_sha256"] is None:
            (root / row["path"]).chmod(0o644)
    (root / "v7").mkdir(mode=0o700)
    for name in SUPPORT:
        private_file(root / "v7" / name, (HERE / "v7" / name).read_bytes())
    rows = registration.sources(root)
    receipt = {"schema": registration.ASSEMBLED, "corpus_version": 7, "sources": rows,
               "source_sha256": registration.digest(registration.canonical(rows)),
               "v6_recipe_sha256": V6_RECIPE_SHA256,
               "v6_receipt_sha256": registration.digest((root / "materialization.json").read_bytes()),
               "v7_patch_sha256": registration.digest(patch.read_bytes()),
               "ported_final_source_sha256": PORT_SOURCE_SHA256, "probe_overlay": probes}
    private_file(root / "assembled.json", json_bytes(receipt))
    identity = registration.verify_assembled(root)
    _rename_new(root, output)
    stage.rmdir()
    return {"assembled_sha256": identity, "source_sha256": receipt["source_sha256"],
            "source_files": len(rows), "v5_source_files": 329, "corpus_version": 7,
            "probe_overlay": probes}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--frozen", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--verify-completion-source", type=Path)
    args = p.parse_args()
    try:
        if args.verify_completion_source:
            verify_port_sources(args.verify_completion_source)
        receipt = materialize(args.frozen, args.output)
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        p.exit(1, f"Refusing V7 materialization: {error}\n")
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
