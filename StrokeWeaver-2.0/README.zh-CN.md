# StrokeWeaver 2.0 · 证据工作台

[English](README.md) · [StrokeWeaver 1.0](../StrokeWeaver-1.0/README.zh-CN.md)

2.0 展示一次生成 MRI 工程资格中的三条实际执行轨迹。原本地闭环串联 `TaskSpec`、冻结 TinyUNet CPU 影像推理、原生空间产物核验、隔离本地模型函数调用，以及技术完成或人工转交。GitHub 版回放原始凭证、核对哈希，并提供两项只读 MCP 查询。原始模型运行环境和权重独立保存。

| 场景 | 实测结果 | 主机全程耗时 |
| --- | --- | ---: |
| 正常 | `STOP`，一次状态工具调用 | 51.73 秒 |
| 证据失效 | `REFER`，等待技术复核，零 LLM 请求 | 3.12 秒 |
| 中断恢复 | `STOP`，复用原产物，零重复前向及计费 | 30.93 秒 |

在 `StrokeWeaver-2.0` 目录使用 Python 3.11 或更高版本：

```shell
python -B verify_release.py
python -m pip install -r workbench/requirements.txt
python -m streamlit run workbench/app.py --server.address 127.0.0.1 --server.port 18783 --browser.gatherUsageStats false
```

打开本机 `http://127.0.0.1:18783/`，可切换场景、逐步查看执行轨迹、检查耗时和转交状态、导出报告。公开工作台的转交状态为只读。MCP 客户端的启动参数见[英文说明](README.md#verify-the-evidence-or-use-mcp)。

本版仅提供生成输入的技术回放。共享强门控、完整有限图 VOI 和原风险约束保留，保护标签继续封存。 [原始凭证清单](evidence_manifest.json)
