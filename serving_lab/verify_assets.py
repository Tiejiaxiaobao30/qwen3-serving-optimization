"""Read-only local asset and workload integrity check."""
import hashlib
import json
from pathlib import Path

from tokenizers import Tokenizer

ROOT = Path(__file__).resolve().parents[1]


def main():
    inventory = json.loads((ROOT / 'reports/model_inventory.json').read_text(encoding='utf-8'))
    assets = ROOT / 'assets/sft42_adapter'
    for item in inventory['files']:
        path = assets / item['file']
        assert hashlib.sha256(path.read_bytes()).hexdigest() == item['sha256'], path
    tokenizer = Tokenizer.from_file(str(assets / 'tokenizer.json'))
    tokenizer.no_padding()
    tokenizer.no_truncation()
    folder = ROOT / 'workloads/v1'
    manifest = json.loads((folder / 'manifest.json').read_text(encoding='utf-8'))
    assert hashlib.sha256((assets / 'tokenizer.json').read_bytes()).hexdigest() == manifest['tokenizer_sha256']
    ids, prompts, counts = set(), set(), {}
    for item in manifest['files']:
        path = folder / item['file']
        assert hashlib.sha256(path.read_bytes()).hexdigest() == item['sha256'], path
        rows = [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]
        assert len(rows) == item['count'], path
        counts[path.name] = len(rows)
        for row in rows:
            assert row['request_id'] not in ids
            ids.add(row['request_id'])
            assert row['prompt'] not in prompts
            prompts.add(row['prompt'])
            assert len(tokenizer.encode(row['prompt'], add_special_tokens=False).ids) == row['prompt_tokens']
            assert row['prompt_tokens'] + row['max_tokens'] <= 2048
    print(json.dumps({'status': 'PASS', 'adapter_files_verified': len(inventory['files']),
                      'requests_verified': len(ids), 'workload_counts': counts,
                      'boundary': 'local data and hashes only, no GPU or model generation'}, indent=2))


if __name__ == '__main__':
    main()
