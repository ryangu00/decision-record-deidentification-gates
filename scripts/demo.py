#!/usr/bin/env python3
"""Run all synthetic stages without sockets; use --http for the loopback listener."""
import argparse
import os
import threading

from mock_server import make_server
from run_pipeline import main as run_pipeline


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--work-dir", required=True)
    ap.add_argument("--http", action="store_true")
    a = ap.parse_args()
    if not a.http:
        os.environ["COOKBOOK_MOCK_MODE"] = "clean"
        return run_pipeline(["--work-dir", a.work_dir])
    os.environ.pop("COOKBOOK_MOCK_MODE", None)
    with make_server() as server:
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        try:
            return run_pipeline(["--work-dir", a.work_dir, "--base",
                                 f"http://127.0.0.1:{server.server_port}/v1"])
        finally:
            server.shutdown()
            worker.join()


if __name__ == "__main__":
    raise SystemExit(main())
