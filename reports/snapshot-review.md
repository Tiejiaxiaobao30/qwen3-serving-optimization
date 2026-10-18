# GPU 实验快照检查与索引

归档包含 **44 组运行、3744 条请求记录、0 条协议/执行失败**。

每组已检查：工作负载 SHA-256、请求 ID 完整性与唯一性、逐请求结果重算的摘要字段。
总时长沿用原 summary.json，未独立重建墙钟时间；本检查不验证运行硬件、预热、缓存清理或模型身份。
成功表示请求完成并符合客户端协议检查，不等同于答案正确。

## 重复运行的原始观察

下表按目录名分组，列出三次运行的吞吐中位数及范围，不构成统一环境下的框架排名或因果加速结论。

| 归档组名 | 次数 | 吞吐中位数 tok/s | 最小–最大 tok/s |
| --- | ---: | ---: | ---: |
| `vllm-confirm-shared-off-c8-*` | 3 | 326.74 | 314.16–337.24 |
| `vllm-confirm-shared-on-c8-*` | 3 | 357.67 | 341.22–383.16 |
| `vllm-final-unique-on-c8-*` | 3 | 350.71 | 345.38–352.12 |
| `sglang-confirm-unique-c8-*` | 3 | 295.96 | 295.92–300.17 |

## 解释边界

- `off/on` 是归档目录中的实验标签，具体缓存设置须回查相应启动日志；不能仅凭目录名确认实际生效。
- 目录没有逐运行绑定完整的模型合并哈希、GPU 环境、预热与缓存重置证据，暂不发布公平框架优劣或稳定加速倍数。
- 所有归档运行均未配置延迟 SLO；不能给出满足业务延迟目标的有效吞吐结论。
- 并发限制模式一次提交整批任务；发送后 TTFT 与包含客户端排队的 offered TTFT 不可混用。
- 质量集为 40 道合成算术题；请求成功率不代表 GSM8K 或通用推理准确率。
- 当前汇总未重跑 GPU 实验，也未访问云端在线服务。

## 全量运行索引

| 运行 | 请求数 | 失败数 | 输出 tok/s | TTFT P95 ms | 排队在内 E2E P95 ms |
| --- | ---: | ---: | ---: | ---: | ---: |
| [sglang-confirm-unique-c8-r1](../results/gpu/sglang-confirm-unique-c8-r1/summary.json) | 200 | 0 | 300.17 | 491.32 | 81882.35 |
| [sglang-confirm-unique-c8-r2](../results/gpu/sglang-confirm-unique-c8-r2/summary.json) | 200 | 0 | 295.96 | 493.19 | 83070.91 |
| [sglang-confirm-unique-c8-r3](../results/gpu/sglang-confirm-unique-c8-r3/summary.json) | 200 | 0 | 295.92 | 488.41 | 83047.06 |
| [sglang-explore-long-c1-r1](../results/gpu/sglang-explore-long-c1-r1/summary.json) | 32 | 0 | 44.53 | 89.50 | 87546.70 |
| [sglang-explore-long-c16-r1](../results/gpu/sglang-explore-long-c16-r1/summary.json) | 32 | 0 | 644.46 | 185.36 | 6354.25 |
| [sglang-explore-long-c4-r1](../results/gpu/sglang-explore-long-c4-r1/summary.json) | 32 | 0 | 172.07 | 106.52 | 23802.49 |
| [sglang-explore-long-c8-r1](../results/gpu/sglang-explore-long-c8-r1/summary.json) | 32 | 0 | 335.35 | 142.28 | 12212.42 |
| [sglang-explore-short-c1-r1](../results/gpu/sglang-explore-short-c1-r1/summary.json) | 32 | 0 | 44.74 | 64.29 | 87159.29 |
| [sglang-explore-short-c16-r1](../results/gpu/sglang-explore-short-c16-r1/summary.json) | 32 | 0 | 651.27 | 239.98 | 6287.57 |
| [sglang-explore-short-c4-r1](../results/gpu/sglang-explore-short-c4-r1/summary.json) | 32 | 0 | 166.93 | 358.38 | 24535.30 |
| [sglang-explore-short-c8-r1](../results/gpu/sglang-explore-short-c8-r1/summary.json) | 32 | 0 | 338.14 | 111.02 | 12112.12 |
| [sglang-quality-c1-r1](../results/gpu/sglang-quality-c1-r1/summary.json) | 40 | 0 | 44.15 | 62.33 | 38415.65 |
| [sglang-smoke-c1-r1](../results/gpu/sglang-smoke-c1-r1/summary.json) | 16 | 0 | 37.78 | 2189.73 | 52049.72 |
| [vllm-confirm-shared-off-c8-r1](../results/gpu/vllm-confirm-shared-off-c8-r1/summary.json) | 200 | 0 | 314.16 | 360.29 | 78549.57 |
| [vllm-confirm-shared-off-c8-r2](../results/gpu/vllm-confirm-shared-off-c8-r2/summary.json) | 200 | 0 | 337.24 | 375.38 | 72474.77 |
| [vllm-confirm-shared-off-c8-r3](../results/gpu/vllm-confirm-shared-off-c8-r3/summary.json) | 200 | 0 | 326.74 | 374.47 | 75499.58 |
| [vllm-confirm-shared-on-c8-r1](../results/gpu/vllm-confirm-shared-on-c8-r1/summary.json) | 200 | 0 | 357.67 | 206.62 | 68969.63 |
| [vllm-confirm-shared-on-c8-r2](../results/gpu/vllm-confirm-shared-on-c8-r2/summary.json) | 200 | 0 | 383.16 | 213.15 | 64187.71 |
| [vllm-confirm-shared-on-c8-r3](../results/gpu/vllm-confirm-shared-on-c8-r3/summary.json) | 200 | 0 | 341.22 | 201.73 | 71898.75 |
| [vllm-confirm-unique-off-c8-r1](../results/gpu/vllm-confirm-unique-off-c8-r1/summary.json) | 200 | 0 | 351.91 | 367.63 | 69964.51 |
| [vllm-confirm-unique-on-c8-r1](../results/gpu/vllm-confirm-unique-on-c8-r1/summary.json) | 200 | 0 | 342.59 | 368.34 | 71868.08 |
| [vllm-explore-long-c1-r1](../results/gpu/vllm-explore-long-c1-r1/summary.json) | 32 | 0 | 51.89 | 67.69 | 75073.95 |
| [vllm-explore-long-c16-r1](../results/gpu/vllm-explore-long-c16-r1/summary.json) | 32 | 0 | 720.85 | 246.11 | 5680.20 |
| [vllm-explore-long-c2-r1](../results/gpu/vllm-explore-long-c2-r1/summary.json) | 32 | 0 | 98.05 | 90.69 | 40336.58 |
| [vllm-explore-long-c4-r1](../results/gpu/vllm-explore-long-c4-r1/summary.json) | 32 | 0 | 193.99 | 109.58 | 21113.31 |
| [vllm-explore-long-c8-r1](../results/gpu/vllm-explore-long-c8-r1/summary.json) | 32 | 0 | 384.31 | 168.57 | 10656.90 |
| [vllm-explore-short-c1-r1](../results/gpu/vllm-explore-short-c1-r1/summary.json) | 32 | 0 | 52.40 | 49.56 | 74354.11 |
| [vllm-explore-short-c16-r1](../results/gpu/vllm-explore-short-c16-r1/summary.json) | 32 | 0 | 766.51 | 147.34 | 5340.95 |
| [vllm-explore-short-c2-r1](../results/gpu/vllm-explore-short-c2-r1/summary.json) | 32 | 0 | 101.51 | 74.35 | 38972.12 |
| [vllm-explore-short-c4-r1](../results/gpu/vllm-explore-short-c4-r1/summary.json) | 32 | 0 | 198.06 | 100.82 | 20679.29 |
| [vllm-explore-short-c8-r1](../results/gpu/vllm-explore-short-c8-r1/summary.json) | 32 | 0 | 393.21 | 112.05 | 10415.27 |
| [vllm-final-unique-on-c8-r1](../results/gpu/vllm-final-unique-on-c8-r1/summary.json) | 200 | 0 | 345.38 | 371.61 | 71252.86 |
| [vllm-final-unique-on-c8-r2](../results/gpu/vllm-final-unique-on-c8-r2/summary.json) | 200 | 0 | 352.12 | 325.59 | 69822.28 |
| [vllm-final-unique-on-c8-r3](../results/gpu/vllm-final-unique-on-c8-r3/summary.json) | 200 | 0 | 350.71 | 377.15 | 70098.65 |
| [vllm-prefix-off-shared-c1-r1](../results/gpu/vllm-prefix-off-shared-c1-r1/summary.json) | 32 | 0 | 50.56 | 82.01 | 77129.61 |
| [vllm-prefix-off-shared-c16-r1](../results/gpu/vllm-prefix-off-shared-c16-r1/summary.json) | 32 | 0 | 583.20 | 992.55 | 7021.39 |
| [vllm-prefix-off-shared-c4-r1](../results/gpu/vllm-prefix-off-shared-c4-r1/summary.json) | 32 | 0 | 162.18 | 359.43 | 25229.26 |
| [vllm-prefix-off-shared-c8-r1](../results/gpu/vllm-prefix-off-shared-c8-r1/summary.json) | 32 | 0 | 340.21 | 487.56 | 12027.98 |
| [vllm-prefix-on-shared-c1-r1](../results/gpu/vllm-prefix-on-shared-c1-r1/summary.json) | 32 | 0 | 49.11 | 65.69 | 79446.45 |
| [vllm-prefix-on-shared-c16-r1](../results/gpu/vllm-prefix-on-shared-c16-r1/summary.json) | 32 | 0 | 701.32 | 273.54 | 5838.59 |
| [vllm-prefix-on-shared-c4-r1](../results/gpu/vllm-prefix-on-shared-c4-r1/summary.json) | 32 | 0 | 186.56 | 128.64 | 21954.64 |
| [vllm-prefix-on-shared-c8-r1](../results/gpu/vllm-prefix-on-shared-c8-r1/summary.json) | 32 | 0 | 375.60 | 152.87 | 10904.04 |
| [vllm-quality-c1-r1](../results/gpu/vllm-quality-c1-r1/summary.json) | 40 | 0 | 49.61 | 60.27 | 33864.48 |
| [vllm-smoke-c1-r1](../results/gpu/vllm-smoke-c1-r1/summary.json) | 16 | 0 | 50.64 | 354.31 | 38586.99 |

离线重建：`python -m serving_lab.summarize_results`。原始 config/requests/summary 文件保持不变。
