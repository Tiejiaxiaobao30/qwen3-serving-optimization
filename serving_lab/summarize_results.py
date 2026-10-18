"""Audit archived results offline and rebuild their CSV/Markdown index (no GPU)."""
import csv
import hashlib
import json
import math
from pathlib import Path
import statistics

from serving_lab.benchmark import summarize


def compare(expected, actual, path=''):
    if isinstance(expected, dict):
        for key, value in expected.items():
            if key not in actual:
                raise ValueError(f'Missing summary field: {path}.{key}')
            compare(value, actual[key], f'{path}.{key}')
    elif isinstance(expected, (int, float)) and not isinstance(expected, bool):
        if not isinstance(actual, (int, float)) or not math.isclose(expected, actual, rel_tol=1e-9, abs_tol=1e-8):
            raise ValueError(f'Summary mismatch: {path}')
    elif expected != actual:
        raise ValueError(f'Summary mismatch: {path}')


def main():
    root = Path(__file__).resolve().parents[1]
    records = []
    for summary_path in sorted((root / 'results/gpu').glob('*/summary.json')):
        run = summary_path.parent
        saved = json.loads(summary_path.read_text(encoding='utf-8'))
        config = json.loads((run / 'config.json').read_text(encoding='utf-8'))
        requests = [json.loads(line) for line in (run / 'requests.jsonl').read_text(encoding='utf-8').splitlines() if line.strip()]
        workload = root / config['workload']
        if hashlib.sha256(workload.read_bytes()).hexdigest() != config['workload_sha256']:
            raise ValueError(f'Workload hash mismatch: {run.name}')
        expected_rows = [json.loads(line) for line in workload.read_text(encoding='utf-8').splitlines() if line.strip()]
        if config.get('limit') is not None:
            expected_rows = expected_rows[:config['limit']]
        ids = [row['request_id'] for row in requests]
        if len(set(ids)) != len(ids) or set(ids) != {row['request_id'] for row in expected_rows}:
            raise ValueError(f'Request IDs do not match workload: {run.name}')
        rebuilt = summarize(requests, saved['duration_s'], config.get('ttft_slo_ms'), config.get('e2e_slo_ms'))
        compare(rebuilt, saved, run.name)
        records.append({
            'run': run.name, 'workload': workload.name,
            'concurrency': config['concurrency'], 'requested': saved['requested'],
            'successful': saved['successful'], 'failed': saved['failed'],
            'output_tok_per_s': saved['output_tok_per_s'],
            'ttft_p95_ms': saved['ttft_ms']['p95'],
            'offered_e2e_p95_ms': saved['offered_e2e_ms']['p95'],
            'evidence_kind': saved['evidence_kind'],
        })
    if not records:
        raise ValueError('No archived GPU runs found')
    reports = root / 'reports'
    with (reports / 'results-overview.csv').open('w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(records[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(records)
    total = sum(row['requested'] for row in records)
    failures = sum(row['failed'] for row in records)
    lines = [
        '# GPU 实验快照检查与索引', '',
        f'归档包含 **{len(records)} 组运行、{total} 条请求记录、{failures} 条协议/执行失败**。', '',
        '每组已检查：工作负载 SHA-256、请求 ID 完整性与唯一性、逐请求结果重算的摘要字段。',
        '总时长沿用原 summary.json，未独立重建墙钟时间；本检查不验证运行硬件、预热、缓存清理或模型身份。',
        '成功表示请求完成并符合客户端协议检查，不等同于答案正确。', '',
        '## 重复运行的原始观察', '',
        '下表按目录名分组，列出三次运行的吞吐中位数及范围，不构成统一环境下的框架排名或因果加速结论。', '',
        '| 归档组名 | 次数 | 吞吐中位数 tok/s | 最小–最大 tok/s |',
        '| --- | ---: | ---: | ---: |',
    ]
    for prefix in ('vllm-confirm-shared-off-c8-', 'vllm-confirm-shared-on-c8-', 'vllm-final-unique-on-c8-', 'sglang-confirm-unique-c8-'):
        values = [r['output_tok_per_s'] for r in records if r['run'].startswith(prefix)]
        if values:
            lines.append(f'| `{prefix}*` | {len(values)} | {statistics.median(values):.2f} | {min(values):.2f}–{max(values):.2f} |')
    lines += [
        '', '## 解释边界', '',
        '- `off/on` 是归档目录中的实验标签，具体缓存设置须回查相应启动日志；不能仅凭目录名确认实际生效。',
        '- 目录没有逐运行绑定完整的模型合并哈希、GPU 环境、预热与缓存重置证据，暂不发布公平框架优劣或稳定加速倍数。',
        '- 所有归档运行均未配置延迟 SLO；不能给出满足业务延迟目标的有效吞吐结论。',
        '- 并发限制模式一次提交整批任务；发送后 TTFT 与包含客户端排队的 offered TTFT 不可混用。',
        '- 质量集为 40 道合成算术题；请求成功率不代表 GSM8K 或通用推理准确率。',
        '- 当前汇总未重跑 GPU 实验，也未访问云端在线服务。',
        '', '## 全量运行索引', '',
        '| 运行 | 请求数 | 失败数 | 输出 tok/s | TTFT P95 ms | 排队在内 E2E P95 ms |',
        '| --- | ---: | ---: | ---: | ---: | ---: |',
    ]
    for row in records:
        name = row['run']
        lines.append(f"| [{name}](../results/gpu/{name}/summary.json) | {row['requested']} | {row['failed']} | {row['output_tok_per_s']:.2f} | {row['ttft_p95_ms']:.2f} | {row['offered_e2e_p95_ms']:.2f} |")
    lines += ['', '离线重建：`python -m serving_lab.summarize_results`。原始 config/requests/summary 文件保持不变。', '']
    (reports / 'snapshot-review.md').write_text('\n'.join(lines), encoding='utf-8', newline='\n')
    print(json.dumps({'runs': len(records), 'requests': total, 'failed': failures, 'summary_recalculation': 'PASS'}))


if __name__ == '__main__':
    main()
