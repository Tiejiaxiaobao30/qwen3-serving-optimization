"""Build a whitelist-only upload ZIP; never include environments or credentials."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError('Refusing overwrite: ' + str(args.output))
    inventory = json.loads((ROOT / 'reports/model_inventory.json').read_text(encoding='utf-8'))
    paths = [ROOT / name for name in ['README.md', 'requirements.txt', 'serving-project-plan.md', '.gitignore']]
    for directory, extensions in [('serving_lab', {'.py'}), ('tests', {'.py', '.jsonl'}),
                                   ('docs', {'.md'}), ('configs', {'.json'}), ('workloads', {'.json', '.jsonl'})]:
        paths.extend(p for p in (ROOT / directory).rglob('*') if p.is_file() and p.suffix in extensions)
    paths.append(ROOT / 'reports/model_inventory.json')
    paths.extend(ROOT / 'assets/sft42_adapter' / row['file'] for row in inventory['files'])
    paths = sorted(set(paths))
    assert all(p.is_relative_to(ROOT) and not p.is_symlink() for p in paths)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    entries = []
    with zipfile.ZipFile(args.output, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=3) as archive:
        for path in paths:
            relative = path.relative_to(ROOT).as_posix()
            entries.append({'file': relative, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                            'bytes': path.stat().st_size})
            archive.write(path, relative)
        manifest = {'schema_version': 1, 'status': 'local preparation only; GPU validation pending',
                    'contains_base_model': False, 'contains_merged_model': False, 'files': entries}
        archive.writestr('BUNDLE_MANIFEST.json', json.dumps(manifest, indent=2) + '\n')
    with zipfile.ZipFile(args.output) as archive:
        assert archive.testzip() is None
        for entry in entries:
            assert hashlib.sha256(archive.read(entry['file'])).hexdigest() == entry['sha256']
    digest = hashlib.sha256(args.output.read_bytes()).hexdigest()
    args.output.with_suffix('.sha256').write_text(digest + '  ' + args.output.name + '\n', encoding='utf-8')
    print(json.dumps({'zip': str(args.output), 'files': len(entries), 'bytes': args.output.stat().st_size,
                      'sha256': digest, 'integrity': 'PASS', 'base_model_included': False}, indent=2))


if __name__ == '__main__':
    main()
