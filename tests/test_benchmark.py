import argparse
import asyncio
from http.server import ThreadingHTTPServer
import json
from pathlib import Path
import tempfile
import threading
import unittest

from serving_lab.benchmark import run, sse_events, summarize
from serving_lab.mock_server import Handler


class MetricsTests(unittest.TestCase):
    def test_failure_denominator_and_goodput_includes_queue(self):
        good = {'success': True, 'completion_tokens': 100, 'ignore_eos': True,
                'queue_ms': 900, 'ttft_ms': 100, 'e2e_ms': 200,
                'offered_ttft_ms': 1000, 'offered_e2e_ms': 1100, 'tpot_estimate_ms': 1}
        bad = {'success': False, 'ignore_eos': True}
        result = summarize([good, bad], 2, 500)
        self.assertEqual(result['output_tok_per_s'], 50)
        self.assertEqual(result['failed'], 1)
        self.assertEqual(result['slo']['qualified'], 0)

    def test_sse_multiline_and_comments(self):
        async def lines():
            for line in [': keepalive', 'data: {"value":', 'data: 42}', '', 'data: [DONE]', '']:
                yield line
        async def collect():
            return [item async for item in sse_events(lines())]
        events = asyncio.run(collect())
        self.assertEqual(json.loads(events[0]), {'value': 42})
        self.assertEqual(events[1], '[DONE]')


class IntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        cls.worker = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.worker.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.worker.join()

    def execute(self, mode='valid', count=4, tokens=3, rate=None):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workload = root / 'workload.jsonl'
            rows = [{'request_id': str(i), 'prompt': mode, 'prompt_tokens': 3,
                     'max_tokens': tokens, 'ignore_eos': True} for i in range(count)]
            workload.write_text('\n'.join(json.dumps(r) for r in rows), encoding='utf-8')
            args = argparse.Namespace(base_url=f'http://127.0.0.1:{self.server.server_port}',
                                      model='mock', workload=workload, output=root / 'run',
                                      concurrency=1, request_rate=rate, timeout=2, limit=None,
                                      ttft_slo_ms=None, e2e_slo_ms=None, evidence_kind='local_mock')
            summary = asyncio.run(run(args))
            raw = [json.loads(line) for line in (args.output / 'requests.jsonl').read_text().splitlines()]
            config = json.loads((args.output / 'config.json').read_text())
            self.assertEqual(config['evidence_kind'], 'local_mock')
            self.assertTrue((args.output / 'summary.json').exists())
            return summary, raw

    def test_real_loopback_stream_and_queue(self):
        summary, raw = self.execute()
        self.assertEqual(summary['successful'], 4)
        self.assertTrue(all(r['completion_tokens'] == 3 for r in raw))
        self.assertTrue(all(r['e2e_ms'] >= r['ttft_ms'] > 0 for r in raw))
        self.assertGreater(max(r['queue_ms'] for r in raw), 20)

    def test_missing_usage_is_failure(self):
        summary, raw = self.execute('missing_usage', 1)
        self.assertEqual(summary['successful'], 0)
        self.assertEqual(summary['output_tok_per_s'], 0)
        self.assertIn('usage', raw[0]['error'])

    def test_missing_done_is_failure(self):
        summary, raw = self.execute('missing_done', 1)
        self.assertEqual(summary['failed'], 1)
        self.assertIn('Incomplete stream', raw[0]['error'])

    def test_http_failure(self):
        summary, raw = self.execute('http_error', 1)
        self.assertEqual(summary['failed'], 1)
        self.assertIn('503', raw[0]['error'])

    def test_wrong_fixed_length_is_failure(self):
        summary, raw = self.execute(tokens=128, count=1)
        self.assertEqual(summary['failed'], 1)
        self.assertIn('expected 128', raw[0]['error'])

    def test_fixed_arrival_rate(self):
        summary, _ = self.execute(count=3, rate=20)
        self.assertEqual(summary['successful'], 3)
        self.assertEqual(summary['load_mode'], 'fixed_arrival_rate')
        self.assertGreaterEqual(summary['duration_s'], 0.1)


if __name__ == '__main__':
    unittest.main()
