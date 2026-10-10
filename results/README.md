# 公开验证记录

这里只包含虚构教学数据的实验记录，不包含作业报告、个人信息或API密钥。

| 文件 | 含义 |
| --- | --- |
| `live_evaluation.json` | 30题×3模式，真实模型最终回答、工具轨迹元数据和usage |
| `source_based_secondary_audit.json` | 90份最终回答的AI来源核查；非人类评审 |
| `robustness.json` | 55个确定性故障/消融运行；不调用模型 |
| `vision_off.json` / `vision_on.json` | 各3个真实模型纯图像对照运行 |
| `test_summary.json` | 本地测试与静态检查汇总 |
| `java_listener.txt` | 实际Java监听示例的线程与顺序输出 |
| `manifest.json` | 公共记录的SHA-256摘要及源码快照 |

评分口径、计时边界和局限详见 [实验说明](../docs/experiments.md)。规则100%不等于全文语义100%正确；拒答也不算正确作答。图片输入实验的3题只证明该输入链路与样例有效。

这些记录是一次真实运行的归档，并不承诺未来API重跑得到逐字相同的答案。
