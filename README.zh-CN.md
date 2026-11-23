# StrokeWeaver Agent

StrokeWeaver 是面向卒中影像科研的工作台。三个版本的演示共用一个 Streamlit 入口，可在侧栏切换。

- **Run a generated workflow** 运行固定合成输入的原生空间核验、条件修复和共享策略对照，检查 NIfTI 输入契约并导出审计。
- **Replay audited evidence** 回放正常完成、证据失效转交及中断恢复三条已审计轨迹，查看分阶段耗时、人工转交和 MCP 核验记录，下载证据报告。
- **3.0 · Handoff dialogue** 通过合成病例体验医生和患者对话、证据溯源、签署状态变更以及交接复核。可在本地配置模型服务，未配置时使用确定性回退。

[打开线上工作台](https://strokeweaver-agent.streamlit.app/) · [许可说明](LICENSE_STATUS.md) · [安全与研究范围](SECURITY.md)

## 本地运行

在仓库根目录使用 Python 3.11 或更新版本。

```shell
python -m pip install -r requirements.txt
python -m streamlit run streamlit_app.py --server.address 127.0.0.1
```

打开 `http://127.0.0.1:8501/`。运行视图执行新的合成技术检查，回放视图校验并展示归档凭证。

## 部署到 Streamlit Community Cloud

仓库填 `shumao469/StrokeWeaver-Agent`，分支填 `main`，入口文件填 `streamlit_app.py`。依赖由根目录的 `requirements.txt` 提供，公开演示所需输入和凭证均随仓库提供。

[1.0 独立运行与说明](StrokeWeaver-1.0/README.zh-CN.md) · [2.0 独立运行与说明](StrokeWeaver-2.0/README.zh-CN.md)
