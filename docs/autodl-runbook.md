# AutoDL 历史上云操作模板

本文保留 2026-10-18 本地准备阶段的上云模板；“待执行”等描述是编写时状态。当前仓库已归档 GPU 实验，入口见 README 与 reports/snapshot-review.md。本模板不能代替实际启动日志或环境锁定文件。AutoDL 账号需用户自行登录，不在聊天或脚本中提供密码、验证码。

## 开卡前

1. 登录后先查看可用实例与镜像，优先已验证支持Qwen3的vLLM镜像，以及能隔离安装SGLang的Linux环境。记录GPU完整名称、CPU/内存、驱动、镜像版本和实际单价。不是卡越贵这个1.7B模型就一定越快。
2. 选定实例前据实际单价、计费粒度、系统/数据盘和开关机规则估算费用。此前约30元目标/50元建议上限是规划，不是充值授权。先按16请求试跑估算剩余用时。
3. 先确认历史Base能否从原云端取回；如需重新下载，来源为`Qwen/Qwen3-1.7B-Base`，历史ModelScope revision为`43ab5b53bd7f37e7e8b2214adcc9178ee11fb0b3`。需核验来源revision可取得、文件完整与tokenizer一致；未核验时不得称与历史Base字节相同。不要下载Instruct替代Base。

## 上传后先检查

解压上传包进入项目目录，先阅读包内README。选择平台明确提供的持久化工作目录，路径以实例为准；不要把模型放在不明确的临时目录。

```bash
python -m pip install -r requirements.txt
python -m serving_lab.verify_assets
python -m unittest discover -s tests -v
python -m serving_lab.local_smoke --output results/cloud-mock-first
nvidia-smi
python -m pip freeze > reports/cloud-client-packages.txt
```

不要直接在已预装的vLLM环境盲目升级torch/transformers。客户端可以独立虚拟环境；两个服务后端也分别隔离。先记录环境，再按现有版本兼容性决定安装方式。

## 准备合并模型

本地上传包有adapter和tokenizer，没有Base权重。以下是模板，替换实际路径；此步骤尚未GPU实测。`merge_model`在合并前检查adapter哈希，在合并后记录文件哈希。Base来源revision是声明值，仍需独立核验。

```bash
python -m serving_lab.merge_model --base /actual/base-snapshot --adapter assets/sft42_adapter --output /actual/new-merged-model --base-source-revision 43ab5b53bd7f37e7e8b2214adcc9178ee11fb0b3
```

两个服务共用这一份合并目录。不可分别合并后直接假定相同。保留原adapter不修改。

## 启动与16请求小试验

先检查所选镜像的命令帮助与后端；下面是待验证模板，不是已运行命令。vLLM和SGLang顺序执行，每次启动后保存版本、完整命令、启动日志和实际缓存状态。仅绑定127.0.0.1，压测客户端在实例内部运行。

```bash
vllm serve /actual/new-merged-model --served-model-name qwen3-sft42 --host 127.0.0.1 --port 8000 --dtype half --tensor-parallel-size 1 --max-model-len 2048
```

```bash
python -m serving_lab.benchmark --model qwen3-sft42 --workload workloads/v1/explore_short.jsonl --limit 16 --concurrency 1 --output results/gpu/vllm-smoke-c1 --evidence-kind gpu_smoke
```

SGLang安装与模型启动命令要与固定版本帮助一致；先确认`/v1/completions`接受相同payload、usage及ignore_eos。任何prompt-token计数差异、未返回usage、输出长度不符、HTTP错误，客户端都会作为失败，不会静默当成功。若有协议差异，修正并重做两端smoke；不在一端单独替换提示词。

## 正式跑之前

- 上面的命令不包含预热。另准备不与正式共享前缀重复的预热请求，完成编译/启动预热后再计时。
- 缓存实验分清冷缓存与热缓存，服务重启或验证过的清缓存后，记录条件。不能让上一轮正式请求给下一轮偷偷预热。
- 先少量探索并发，再冻结少数确认配置；详细计划见configs/experiments.json，不做全组合遍历。
- 收集小型质量集自然生成结果；`ignore_eos=True`的固定长度容量测试不证明回答质量。
- 第一次先看失败率和原始输出，再看吞吐。输出目录拒绝覆盖，失败后使用新run_id保存证据。
- 结束时下载配置、逐请求JSONL、摘要、服务日志、GPU/包版本与merge_provenance，核对文件；再确认停止GPU计费。磁盘单独计费规则以平台为准。

## 本次看到的公开价格，仅作参考

2026-10-18 AutoDL首页普通用户显示4090 1.88元/小时、A800-80GB 5.59元/小时、H800 9.98元/小时。不是实际选定实例报价，不代表可用库存或最终账单。实际下单页和账号权益优先。来源：https://www.autodl.com/home
