"""GPU preparation step; requires separately installed torch/transformers/peft."""
import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path
import shutil


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', type=Path, required=True, help='Existing local Base snapshot, not an adapter directory')
    parser.add_argument('--adapter', type=Path, default=Path('assets/sft42_adapter'))
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--base-source-revision', required=True, help='Declared provenance; file hashes are recorded independently')
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError('Refusing to overwrite output: ' + str(args.output))
    base_config = json.loads((args.base / 'config.json').read_text())
    if base_config.get('model_type') != 'qwen3' or base_config.get('hidden_size') != 2048:
        raise ValueError('Expected Qwen3-1.7B-Base architecture; inspect the local snapshot')
    actual = hashlib.sha256((args.adapter / 'adapter_model.safetensors').read_bytes()).hexdigest()
    if actual != '63420f32629bbf452b30b4e5d27060c924f01b37dea013a073bb2956cea2437f':
        raise ValueError('Adapter does not match archived SFT seed42 evidence')
    import torch
    from transformers import AutoModelForCausalLM
    from peft import PeftModel
    base = AutoModelForCausalLM.from_pretrained(str(args.base), dtype=torch.float16, device_map={'': 0},
                                             local_files_only=True, trust_remote_code=False)
    merged = PeftModel.from_pretrained(base, str(args.adapter), local_files_only=True).merge_and_unload()
    merged.save_pretrained(str(args.output), safe_serialization=True)
    for name in ['tokenizer.json', 'tokenizer_config.json', 'special_tokens_map.json',
                 'added_tokens.json', 'vocab.json', 'merges.txt']:
        source = args.adapter / name
        if source.exists():
            shutil.copy2(source, args.output / name)
    def hashes(folder):
        result = {}
        for path in sorted(folder.iterdir()):
            if path.is_file() and path.suffix in ('.json', '.safetensors', '.txt', '.model'):
                digest = hashlib.sha256()
                with path.open('rb') as data:
                    for chunk in iter(lambda: data.read(8 * 1024 * 1024), b''):
                        digest.update(chunk)
                result[path.name] = digest.hexdigest()
        return result
    provenance = {'base_source_revision_declared': args.base_source_revision,
                  'revision_identity_independently_verified': False,
                  'base_files_sha256': hashes(args.base), 'adapter_sha256': actual,
                  'merged_files_sha256': hashes(args.output),
                  'packages': {key: importlib.metadata.version(key) for key in ['torch', 'transformers', 'peft']},
                  'dtype': 'float16'}
    (args.output / 'merge_provenance.json').write_text(json.dumps(provenance, indent=2) + '\n', encoding='utf-8')
    print('Merged model saved with file hashes. Run generation and protocol checks before benchmarking.')


if __name__ == '__main__':
    main()
