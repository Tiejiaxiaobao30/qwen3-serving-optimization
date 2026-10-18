# Qwen3 推理服务评测与性能优化

当前快照包含云端 GPU 实验原始记录；结果汇总及公平比较结论尚待审计。目标是复用已有Qwen3 SFT模型，在固定工作负载下比较vLLM/SGLang，验证并发与前缀缓存的收益、延迟代价和适用边界。

上游训练项目：[qwen3-math-posttraining](https://github.com/Tiejiaxiaobao30/qwen3-math-posttraining)。本项目不重新训练，也不改动原官方封存评测。

## 已有本地内容

- 从原备份只提取SFT seed42 adapter和tokenizer，adapter SHA256与历史证据匹配；见`reports/model_inventory.json`。此段为本地准备阶段记录；云端运行状态以 reports/ 与 results/gpu/ 的快照为准。
- `workloads/v1/`：696条性能请求（128/1024输入token，含约774token共享前缀条件）和40条独立算术检查题；合成来源、长度、哈希及限制见manifest。
- `serving_lab/benchmark.py`：统一异步流式completion客户端，支持并发限制、固定到达率、逐请求原始结果、队列/TTFT/E2E、估算TPOT、服务端token计数及可选延迟目标。
- `tests/`：本地回环服务集成测试及指标边界测试。mock结果不是GPU性能。
- `configs/experiments.json`：探索/缓存对照/少量重复确认的计划，正式阈值尚未冻结。

## Windows本地使用

```powershell
.\.venv\Scripts\python.exe -m serving_lab.verify_assets
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m serving_lab.local_smoke --output results/local-smoke-new
```

首次安装环境：`python -m venv .venv`，然后`.\.venv\Scripts\python.exe -m pip install -r requirements.txt`。当前目录现有环境已安装；无需重复安装。数据已经冻结，构建器默认拒绝覆盖JSONL；需要新版本时使用新`--output`目录。

## 指标边界

TTFT测首个非空内容事件。TPOT由首/末内容事件与服务端completion_tokens估算，不是逐token ITL。没有usage、未完成流、tokenizer计数不一致和固定输出长度不一致均记失败。吞吐分子只计成功请求输出，分母为整个测量批次墙钟时间。延迟分位数只统计成功请求，并单独报告失败率。

并发模式是一次提交整个批次、限制同时在途请求，客户端等待单独记录；固定到达率模式按预定时间发起。可选延迟目标从offered时间计算，包含客户端准入等待；二者不混作同一种业务流量。没有服务端环境证据的run不能用于公平框架比较。

## 下一步

先读`docs/01-first-learning-step.md`，只学习TTFT与总吞吐。上云按照`docs/autodl-runbook.md`，先确定实例与模型来源，16请求小试验通过后再扩展。完整范围见`serving-project-plan.md`。

不将合成数据写成生产流量，不把框架自带机制写成自己实现，不把本地mock结果写进简历。学习和面试材料以实际完成的实验逐步补充。


## 上传快照来源

代码、工作负载、GPU 原始结果与日志来自 2026-10-18 下载的云端备份；docs、configs、tests、requirements 与原计划来自同日本机准备目录，未逐字核对云端版本。此副本不保证包含备份生成后的云端变更。详见 SNAPSHOT_PROVENANCE.json。
