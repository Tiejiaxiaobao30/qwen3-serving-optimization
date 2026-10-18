"""Unified streaming /v1/completions client. Local mock runs are NOT GPU evidence."""
import argparse
import asyncio
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import re
import time

import httpx


async def sse_events(lines):
    """SSE events may span several lines; comments and empty keepalives are ignored."""
    data = []
    async for line in lines:
        if line == '':
            if data:
                yield '\n'.join(data)
                data = []
        elif line.startswith('data:'):
            data.append(line[5:].removeprefix(' '))
    if data:
        yield '\n'.join(data)


def percentile(values, percent):
    values = sorted(values)
    if not values:
        return None
    pos = (len(values) - 1) * percent / 100
    lo, hi = math.floor(pos), math.ceil(pos)
    return values[lo] + (values[hi] - values[lo]) * (pos - lo)


def summarize(rows, duration, ttft_slo_ms=None, e2e_slo_ms=None):
    successful = [r for r in rows if r['success']]
    result = {'requested': len(rows), 'successful': len(successful),
              'failed': len(rows) - len(successful), 'duration_s': duration,
              'success_req_per_s': len(successful) / duration,
              'output_tok_per_s': sum(r['completion_tokens'] for r in successful) / duration,
              'latency_population': 'successful requests only; failures reported separately',
              'percentile_method': 'linear interpolation',
              'tpot_note': 'estimated from first/last content event and server token count; not per-token ITL',
              'slo': None}
    for key in ['queue_ms', 'ttft_ms', 'e2e_ms', 'offered_ttft_ms', 'offered_e2e_ms', 'tpot_estimate_ms']:
        values = [r[key] for r in successful if r.get(key) is not None]
        result[key] = {'p50': percentile(values, 50), 'p95': percentile(values, 95),
                       'mean': sum(values) / len(values) if values else None}
    if ttft_slo_ms is not None or e2e_slo_ms is not None:
        eligible = [r for r in successful
                    if (ttft_slo_ms is None or r['offered_ttft_ms'] <= ttft_slo_ms)
                    and (e2e_slo_ms is None or r['offered_e2e_ms'] <= e2e_slo_ms)]
        result['slo'] = {'ttft_ms': ttft_slo_ms, 'e2e_ms': e2e_slo_ms,
                         'timing_origin': 'offered time, including client admission delay',
                         'qualified': len(eligible), 'fraction_of_all_requests': len(eligible) / len(rows),
                         'qualified_req_per_s': len(eligible) / duration}
    quality = [r for r in rows if not r['ignore_eos'] and r.get('expected_answer') is not None]
    if quality:
        correct = sum(r['success'] and r.get('parsed_answer') == r['expected_answer'] for r in quality)
        result['quality'] = {'total': len(quality), 'correct': correct, 'accuracy': correct / len(quality),
                              'scope': 'synthetic arithmetic smoke only'}
    return result


async def request_one(client, semaphore, row, args, offered_at):
    await asyncio.sleep(max(0, offered_at - time.perf_counter()))
    result = {'request_id': row['request_id'], 'success': False, 'error': None,
              'ignore_eos': row['ignore_eos'], 'expected_answer': row.get('expected_answer'),
              'completion_tokens': None, 'response_text': '', 'finish_reason': None}
    async with semaphore:
        sent_at = time.perf_counter()
        result['queue_ms'] = (sent_at - offered_at) * 1000
        first, last, usage, done = None, None, None, False
        payload = {'model': args.model, 'prompt': row['prompt'], 'max_tokens': row['max_tokens'],
                   'temperature': 0, 'stream': True, 'stream_options': {'include_usage': True},
                   'ignore_eos': row['ignore_eos']}
        try:
            async with asyncio.timeout(args.timeout), client.stream('POST', args.base_url.rstrip('/') + '/v1/completions', json=payload) as response:
                response.raise_for_status()
                async for data in sse_events(response.aiter_lines()):
                    if data.strip() == '[DONE]':
                        done = True
                        break
                    event = json.loads(data)
                    if event.get('error'):
                        raise ValueError('Server stream error: ' + str(event['error']))
                    if event.get('usage') is not None:
                        usage = event['usage']
                    for choice in event.get('choices', []):
                        if choice.get('index', 0) != 0:
                            continue
                        text = choice.get('text', '')
                        if text:
                            now = time.perf_counter()
                            if first is None:
                                first = now
                            last = now
                            result['response_text'] += text
                        if choice.get('finish_reason') is not None:
                            result['finish_reason'] = choice['finish_reason']
            completed = time.perf_counter()
            if not done or result['finish_reason'] not in ('stop', 'length'):
                raise ValueError('Incomplete stream: missing DONE or successful finish_reason')
            if first is None or usage is None:
                raise ValueError('Missing nonempty content or server usage; cannot report token throughput')
            tokens = usage.get('completion_tokens')
            if not isinstance(tokens, int) or isinstance(tokens, bool) or tokens <= 0:
                raise ValueError('Invalid server completion token count')
            if usage.get('prompt_tokens') != row['prompt_tokens']:
                raise ValueError(f"Tokenizer/protocol mismatch: expected {row['prompt_tokens']}, got {usage.get('prompt_tokens')}")
            if row['ignore_eos'] and tokens != row['max_tokens']:
                raise ValueError(f'Fixed-output workload expected {row["max_tokens"]} tokens, got {tokens}')
            result.update(success=True, completion_tokens=tokens,
                          ttft_ms=(first - sent_at) * 1000, e2e_ms=(completed - sent_at) * 1000,
                          offered_ttft_ms=(first - offered_at) * 1000,
                          offered_e2e_ms=(completed - offered_at) * 1000,
                          tpot_estimate_ms=(last - first) * 1000 / (tokens - 1) if tokens > 1 else None,
                          usage=usage)
            matches = re.findall(r'^Final answer:\s*(-?\d+(?:\.\d+)?)\s*$', result['response_text'], re.M)
            result['parsed_answer'] = matches[0] if len(matches) == 1 else None
        except (httpx.HTTPError, ValueError, KeyError, TypeError, TimeoutError) as exc:
            result['error'] = type(exc).__name__ + ': ' + str(exc)
            result['elapsed_until_error_ms'] = (time.perf_counter() - sent_at) * 1000
    return result


async def run(args):
    if args.concurrency <= 0 or args.timeout <= 0 or args.request_rate is not None and args.request_rate <= 0:
        raise ValueError('Concurrency, timeout and request rate must be positive')
    rows = [json.loads(line) for line in args.workload.read_text(encoding='utf-8').splitlines() if line.strip()]
    if args.limit is not None:
        if args.limit <= 0:
            raise ValueError('Limit must be positive')
        rows = rows[:args.limit]
    if not rows or len({r['request_id'] for r in rows}) != len(rows):
        raise ValueError('Empty workload or duplicate request IDs')
    args.output.mkdir(parents=True, exist_ok=False)
    config = {k: str(v) if isinstance(v, Path) else v for k, v in vars(args).items()}
    config.update(created_at=datetime.now(timezone.utc).isoformat(), python=platform.python_version(),
                  httpx=httpx.__version__, workload_sha256=hashlib.sha256(args.workload.read_bytes()).hexdigest(),
                  load_mode='fixed_arrival_rate' if args.request_rate else 'bulk_batch_with_concurrency_limit',
                  warmup='none in this command; must be performed separately and cache state recorded',
                  backend_facts='engine/model/GPU config must be collected separately; not inferred from endpoint')
    (args.output / 'config.json').write_text(json.dumps(config, indent=2) + '\n', encoding='utf-8')
    headers = {}
    if os.getenv('SERVING_API_KEY'):
        headers['Authorization'] = 'Bearer ' + os.environ['SERVING_API_KEY']
    semaphore = asyncio.Semaphore(args.concurrency)
    async with httpx.AsyncClient(timeout=args.timeout, headers=headers, trust_env=False,
                                 limits=httpx.Limits(max_connections=args.concurrency)) as client:
        started = time.perf_counter()
        tasks = [request_one(client, semaphore, row, args,
                             started + i / args.request_rate if args.request_rate else started)
                 for i, row in enumerate(rows)]
        with (args.output / 'requests.jsonl').open('x', encoding='utf-8') as out:
            results = []
            for task in asyncio.as_completed(tasks):
                item = await task
                results.append(item)
                out.write(json.dumps(item, ensure_ascii=False) + '\n')
                out.flush()
                done = len(results)
                if done == 1 or done % max(1, len(rows) // 8) == 0 or done == len(rows):
                    ok = sum(bool(r.get("success")) for r in results)
                    print(f"[progress] {done}/{len(rows)} | success={ok} failed={done-ok} elapsed={time.perf_counter()-started:.1f}s", flush=True)
        elapsed = time.perf_counter() - started
    summary = summarize(results, elapsed, args.ttft_slo_ms, args.e2e_slo_ms)
    summary.update(evidence_kind=args.evidence_kind, load_mode=config['load_mode'])
    (args.output / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url', default='http://127.0.0.1:8000')
    parser.add_argument('--model', required=True)
    parser.add_argument('--workload', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--concurrency', type=int, default=1)
    parser.add_argument('--request-rate', type=float)
    parser.add_argument('--timeout', type=float, default=120)
    parser.add_argument('--limit', type=int)
    parser.add_argument('--ttft-slo-ms', type=float)
    parser.add_argument('--e2e-slo-ms', type=float)
    parser.add_argument('--evidence-kind', choices=['local_mock', 'gpu_smoke', 'gpu_exploration', 'gpu_confirmation'], required=True)
    args = parser.parse_args()
    summary = asyncio.run(run(args))
    print(json.dumps(summary, indent=2))
    if summary['failed']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
