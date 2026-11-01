# RoboIDF

2026-11-01：M0 无真机合成闭环。当前范围：数据与模型合同、合成 Mock Robot、两参数最小二乘、独立轨迹自由回放与 JSON 报告。

## 快速开始

```bash
pixi install --locked
pixi run --locked test
pixi run --locked demo
```

运行结果保存在 `artifacts/`，不提交生成文件。环境为 Linux x86_64 / Python 3.12，依赖由 Pixi 锁定。单独克隆本仓库即可运行。

## 边界

M0 只验证离散单自由度质量阻尼系统与离线数据流程，不是机械臂动力学、真实设备辨识或 Agent 实现。Tianji Arm、Wuji Hand 2、安全执行器、MuJoCo / Isaac 后端均未接入。无噪声同模型的精确恢复不代表现实性能。项目许可证尚未确定。

Core 维护 `m0.v1` 合同，Bench 与 Ecosystem 固定 Core Git 版本，升级必须重新运行测试。训练与保留集使用不同激励；最终测试只用于验收。

## 社区协作

见 [贡献指南](CONTRIBUTING.md) 和 [M0 使用说明](docs/m0.md)。问题与贡献请在对应 GitHub 仓库提交，附复现命令、版本、输入来源与实际结果。不要提交凭据、未经授权的真机数据或受限资产。

[Core](https://github.com/RoboIDF/RoboIDF) · [Bench](https://github.com/RoboIDF/RoboIDF-Bench) · [Ecosystem](https://github.com/RoboIDF/RoboIDF-Ecosystem)

[早期规划与历史状态](docs/pre-m0-status.md) 保留作背景，冲突时以本文为准。论文工作及 Overleaf 接入已按用户要求停止，既有文件保留。
