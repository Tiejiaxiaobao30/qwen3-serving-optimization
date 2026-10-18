"""Persist one mock-only end-to-end run and shut down its loopback server."""
import argparse
import asyncio
from http.server import ThreadingHTTPServer
import json
from pathlib import Path
import threading

from serving_lab.benchmark import run
from serving_lab.mock_server import Handler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        settings = argparse.Namespace(base_url=f'http://127.0.0.1:{server.server_port}', model='MOCK-NO-MODEL',
                                      workload=Path(__file__).resolve().parents[1] / 'tests/fixtures/mock.jsonl',
                                      output=args.output, concurrency=2, request_rate=None,
                                      timeout=10, limit=None, ttft_slo_ms=None, e2e_slo_ms=None,
                                      evidence_kind='local_mock')
        result = asyncio.run(run(settings))
        print(json.dumps({'status': 'PASS' if result['failed'] == 0 else 'FAIL',
                          'successful_mock_requests': result['successful'], 'evidence_kind': 'local_mock',
                          'warning': 'Synthetic server only. These numbers are not model/GPU performance.'}, indent=2))
        if result['failed']:
            raise SystemExit(1)
    finally:
        server.shutdown()
        server.server_close()
        worker.join()


if __name__ == '__main__':
    main()
