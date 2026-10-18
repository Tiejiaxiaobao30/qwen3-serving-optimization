"""Construct synthetic math workloads without touching the sealed GSM8K test."""
import argparse
import hashlib
import json
from pathlib import Path

from tokenizers import Tokenizer

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = 'Solve the following math problem step by step.\nEnd with exactly: Final answer: <number>\n\n'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_jsonl(path, rows):
    with path.open('x', encoding='utf-8', newline='\n') as out:
        for row in rows:
            out.write(json.dumps(row, ensure_ascii=False) + '\n')


def construct(tokenizer, text, target):
    # Padding is deliberately disclosed synthetic instructional text, not real traffic.
    filler = ' Check the quantities, units, and arithmetic before writing the final answer.'
    text += '\nReasoning guidance:'
    while len(tokenizer.encode(text, add_special_tokens=False).ids) < target + 32:
        text += filler
    ids = tokenizer.encode(text, add_special_tokens=False).ids[:target]
    rendered = tokenizer.decode(ids, skip_special_tokens=False)
    # Text APIs can retokenize at a truncated boundary. Keep the measured result.
    actual = tokenizer.encode(rendered, add_special_tokens=False).ids
    assert abs(len(actual) - target) <= 4
    return rendered, actual


def common_prefix(a, b):
    for i, (x, y) in enumerate(zip(a, b)):
        if x != y:
            return i
    return min(len(a), len(b))


def build(output, tokenizer_path, explore_count=32, confirm_count=200):
    output.mkdir(parents=True, exist_ok=True)
    tokenizer = Tokenizer.from_file(str(tokenizer_path))
    tokenizer.no_padding()
    tokenizer.no_truncation()
    shared, _ = construct(tokenizer, PROTOCOL + 'Mathematics tutoring session.\n', 768)
    records, inventory = [], []
    for split, count, offset in [('explore', explore_count, 10000), ('confirm', confirm_count, 20000)]:
        for bucket, target in [('short', 128), ('long_unique', 1024), ('long_shared', 1024)]:
            rows = []
            for i in range(count):
                index = offset + i
                a, b = index + 17, index * 3 + 11
                question = f'A shop has {a} notebooks and receives {b} more. How many notebooks does it have now?'
                if bucket == 'long_shared':
                    text = shared + f'\nExercise {index}.\n' + question
                else:
                    # Differ early to prevent the long common filler becoming a prefix hit.
                    text = f'Exercise identifier {index}.\n' + PROTOCOL + question
                prompt, ids = construct(tokenizer, text, target)
                row = {
                    'request_id': f'{split}-{bucket}-{i:04d}', 'split': split,
                    'bucket': bucket, 'prompt': prompt, 'prompt_tokens': len(ids),
                    'prompt_sha256': hashlib.sha256(prompt.encode()).hexdigest(),
                    'max_tokens': 128, 'ignore_eos': True,
                    'source': 'deterministic synthetic arithmetic; instructional repetition for length control',
                    'shared_prefix_group': f'{split}-tutor' if bucket == 'long_shared' else None,
                    'expected_answer': str(a + b),
                }
                rows.append(row)
            token_lists = [tokenizer.encode(r['prompt'], add_special_tokens=False).ids for r in rows]
            common = [common_prefix(a, b) for a, b in zip(token_lists, token_lists[1:])]
            path = output / f'{split}_{bucket}.jsonl'
            write_jsonl(path, rows)
            inventory.append({'file': path.name, 'count': len(rows), 'sha256': digest(path),
                              'min_tokens': min(map(len, token_lists)), 'max_tokens': max(map(len, token_lists)),
                              'adjacent_shared_prefix_min': min(common) if common else None,
                              'adjacent_shared_prefix_max': max(common) if common else None})
            records.extend(rows)
    quality = []
    for i in range(40):
        a, b, c = 73 + 17 * i, 19 + 11 * i, 2 + i % 7
        question = f'A library has {a} books, receives {b} more, then lends out {c}. How many books remain?'
        prompt = PROTOCOL + question
        quality.append({'request_id': f'quality-{i:03d}', 'bucket': 'quality', 'prompt': prompt,
                        'prompt_tokens': len(tokenizer.encode(prompt, add_special_tokens=False).ids),
                        'max_tokens': 256, 'ignore_eos': False, 'expected_answer': str(a + b - c),
                        'source': 'deterministic synthetic arithmetic, addition then subtraction'})
    quality_path = output / 'quality.jsonl'
    write_jsonl(quality_path, quality)
    inventory.append({'file': quality_path.name, 'count': len(quality), 'sha256': digest(quality_path)})
    assert len({r['prompt_sha256'] for r in records}) == len(records), 'Duplicate prompts'
    assert all(r['prompt_tokens'] + r['max_tokens'] <= 2048 for r in records)
    manifest = {'schema_version': 1, 'status': 'constructed, not GPU-tested',
                'tokenizer_sha256': digest(tokenizer_path), 'seed': 'no RNG; formula-based IDs',
                'performance_requests': len(records), 'quality_requests': len(quality),
                'excluded_source': 'GSM8K official sealed test; no test files read',
                'limitations': ['Synthetic workload, not production traffic',
                                'Quality set is easy arithmetic, not a general reasoning benchmark',
                                'Long prompts contain disclosed instructional repetition',
                                'Same lengths do not imply the same semantics or prefill cost'],
                'files': inventory}
    (output / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return manifest


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--tokenizer', type=Path, default=ROOT / 'assets/sft42_adapter/tokenizer.json')
    parser.add_argument('--output', type=Path, default=ROOT / 'workloads/v1')
    args = parser.parse_args()
    print(json.dumps(build(args.output, args.tokenizer), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
