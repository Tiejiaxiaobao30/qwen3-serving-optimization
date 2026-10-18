# Qwen3 推理服务评测与性能优化

基于已有 Qwen3 SFT 模型的推理服务实验项目，使用统一流式客户端记录 vLLM / SGLang 在不同输入长度、并发和前缀复用条件下的吞吐、首响应延迟与排队代价。

**当前状态：已归档真实 GPU 实验，离线结果一致性检查通过；公平框架比较与稳定加速结论仍待补齐实验控制证据。**

上游训练项目：[qwen3-math-posttraining](https://github.com/Tiejiaxiaobao30/qwen3-math-posttraining)。本仓库负责服务与评测，不重新训练模型。

## 项目内容

- **统一客户端**：异步请求、SSE 流解析、并发限制与固定到达率、逐请求落盘、失败检查，以及吞吐、TTFT、E2E、排队与估算 TPOT 指标。
- **合成工作负载**：696 条性能请求与 40 条算术检查题；性能输入包含 128 / 1024 token 条件和共享前缀条件，文件数量与哈希见 [manifest](workloads/v1/manifest.json)。
- **完整运行记录**：44 组 GPU 实验，保留各组配置、逐请求原始结果、摘要和关键服务日志。
- **离线检查**：校验工作负载哈希、请求 ID 与记录完整性，从逐请求记录重算摘要；本地测试覆盖协议、失败判定与指标边界。

vLLM、SGLang 及缓存机制来自上游框架。本项目提供评测工具、实验组织和结果分析，未实现新的推理引擎或缓存算法。

## 实验结果入口

| 内容 | 可核实状态 |
| --- | --- |
| GPU 原始运行 | 44 组，合计 3,744 条请求记录 |
| 协议 / 执行失败 | 归档合计 0 条；不代表答案全部正确 |
| 离线一致性检查 | 44 组工作负载哈希、请求 ID、摘要重算通过 |
| 本地测试 | 8 项通过，只验证客户端与指标逻辑 |
| 框架排名、稳定加速倍数 | 尚需逐运行绑定环境与控制条件，暂不下结论 |

查看 [实验检查与全量索引](reports/snapshot-review.md) 或 [汇总 CSV](reports/results-overview.csv)。所有数值可回查原始运行目录，包含探索与重复运行。

以下为三次重复运行的归档观察。组名沿用历史标签，不能仅凭目录名确认实际缓存状态；这些数值不构成公平跨框架比较。

| 归档组 | 吞吐中位数 tok/s | 三次范围 tok/s |
| --- | ---: | ---: |
| vLLM shared / off / C8 | 326.74 | 314.16–337.24 |
| vLLM shared / on / C8 | 357.67 | 341.22–383.16 |
| vLLM final unique / on / C8 | 350.71 | 345.38–352.12 |
| SGLang confirm unique / C8 | 295.96 | 295.92–300.17 |

合成负载的观察不外推为生产性能。当前未冻结业务延迟 SLO，容量吞吐也不等同于满足业务延迟要求的有效吞吐。

## 目录

```text
serving_lab/                 客户端、工作负载构建、模型准备、离线检查
configs/experiments.json     原始计划，不是执行状态表
workloads/v1/               冻结工作负载与生成 manifest
results/gpu/<run>/          config.json、requests.jsonl、summary.json
reports/                    关键日志、部分环境证据、派生汇总
tests/                      回环服务与指标测试，含 mock fixture
docs/                       历史上云模板与学习说明
requirements.txt            客户端依赖，不包含 GPU 服务后端
SNAPSHOT_PROVENANCE.json     首次导入的来源、哈希与脱敏记录
```

## 本地检查：不需要 GPU 或模型权重

参考客户端环境为 **Python 3.12**；代码使用 `asyncio.timeout`，至少需要 Python 3.11。以下命令在仓库根目录执行。

Windows：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m serving_lab.summarize_results
.\.venv\Scripts\python.exe -m serving_lab.local_smoke --output results/local-smoke-new
```

Linux / macOS：

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m serving_lab.summarize_results
.venv/bin/python -m serving_lab.local_smoke --output results/local-smoke-new
```

`local_smoke` 只使用合成回环服务，不能作为 GPU 性能证据；输出目录必须不存在，重复运行时换目录名。`summarize_results` 只读取归档运行并重建 CSV 和报告，不访问在线模型服务。

权重、adapter 与 tokenizer 资产未纳入 Git。`verify_assets` / `merge_model` 需要另外准备资产，不属于克隆后可直接执行的检查。

## GPU 实验复现入口

归档服务名为 `qwen3-sft42`，配置指向 Qwen3-1.7B SFT seed42 合并模型。来源与已有哈希记录见 [模型清单](reports/model_inventory.json)；服务名不能证明不同运行使用了同一份模型。

已有快照记录包含 NVIDIA GeForce RTX 3080 Ti 12 GB、Python 3.12.3、vLLM `0.20.0+cu129`；SGLang 服务信息记录版本 `0.5.22`。这些证据不能保证每组环境完全一致，需回查 [环境记录](reports/env/) 与 [服务日志](reports/)。驱动显示的 CUDA 版本不等同于所有软件包的运行时版本。

先准备独立服务环境及合并模型，核对模型哈希、GPU、版本、启动参数、预热和缓存状态。已有服务正常运行时，不要为阅读本仓库重复启动或下载模型。服务就绪后，客户端调用示例为：

```bash
python -m serving_lab.benchmark \
  --base-url http://127.0.0.1:8000 \
  --model qwen3-sft42 \
  --workload workloads/v1/explore_short.jsonl \
  --limit 16 --concurrency 1 \
  --output results/gpu/new-smoke-c1 \
  --evidence-kind gpu_smoke
```

准备流程见 [历史上云模板](docs/autodl-runbook.md)。该模板与 [实验计划](configs/experiments.json) 保留编写时状态，不代表当前执行状态。工作负载 manifest 的 `not GPU-tested` 也是生成时状态，执行证据以 `results/gpu/` 为准。

`requirements.txt` 固定客户端依赖；仓库尚无两套 GPU 后端的完整锁定文件，不能只靠此文件重建服务环境。密钥仅通过环境变量 `SERVING_API_KEY` 读取，不写入版本库。

## 指标口径与限制

- **输出吞吐**：成功请求输出 token 总数 ÷ 整批测量墙钟时间，不是单用户生成速度。
- **TTFT**：发送请求至首个非空内容事件，不把 HTTP 响应头当首 token。
- **排队与 E2E**：`ttft_ms` / `e2e_ms` 从发送起算；`offered_*` 从计划到达时起算，包含客户端准入等待。
- **TPOT**：由首末内容事件与服务端 token 数估算，不是逐 token ITL。
- **失败与质量**：缺少 usage、流未完整结束、prompt token 计数不符、固定输出长度不符等记失败；延迟分位数只统计成功请求。40 道合成算术题不代表 GSM8K 或通用推理能力。
- **负载与缓存**：并发限制批处理和固定到达率不可混用口径；缓存收益需核对预热、清理与轮次顺序。缺少逐运行环境证据时，不发布框架优劣或稳定加速结论。

## 来源与后续工作

代码、工作负载、GPU 结果与日志来自 2026-10-18 下载的云端备份。初始 docs、configs、tests、客户端依赖与计划来自同日本机目录，未逐字核对云端版本；备份之后的云端变更尚未核对。本次整理新增离线汇总工具与报告，并更新项目说明。

原始压缩包保留在本机。上传副本排除权重、adapter、环境、缓存、临时文件与压缩包，日志中的内网 IP 和邮箱已遮盖，见 [来源清单](SNAPSHOT_PROVENANCE.json)。该清单为首次导入基线；后续脚本与文档变更以 Git 历史为准。

下一步补齐逐运行模型、环境、预热与缓存证据，冻结延迟目标，再决定是否需要新实验。简历与报告只采用可核实观察，不把框架原生功能或计划写成个人实现成果。
