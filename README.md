# RoboIDF

2026-11-01：开发版，提供可运行的离线工作流、SciPy 辨识后端和验证工具。**v0.2 尚未发布，必须全部 M0–M5 验收后才能发布。**

## 运行

```bash
pixi install --locked
pixi run --locked test
pixi run --locked demo-all
```

Linux x86_64 / Python 3.12，统一使用 Pixi 锁定依赖。各报告位于 `artifacts/`，不提交生成数据。可单独克隆，不需要父目录或其他仓库。

| 命令 | 当前实现 | 文档 |
|---|---|---|
| `pixi run demo` | M0 质量阻尼合成辨识与自由回放 | [M0](docs/m0.md) |
| `pixi run workflow-demo` | M1 持久化状态、工具调用预算、目录锁、失败记录与中断恢复 | [工作流](docs/workflow.md) |
| `pixi run identify-demo` | M3 SciPy 有界优化、局部可辨识性诊断、验证集拒绝 | [后端与激励](docs/backends.md) |
| `pixi run validate-demo` | M2/M4 描述、硬件预检查、模型文件结构及轨迹误差工具 | [验证合同](docs/validation.md) |

M1 当前固定离线工具序列，不是 LLM Agent；M3 只针对标量质量阻尼模型，不是通用机械臂辨识器。SciPy 是已集成的数值优化后端；MuJoCo SysID、Isaac、SDK 与真实设备均未接入。模型结构有效不等于数字孪生验证通过。硬件执行始终不可用。

## 跨项目协作

Core 维护合同与工具；[Bench](https://github.com/RoboIDF/RoboIDF-Bench) 独立生成最终测试与对照；[Ecosystem](https://github.com/RoboIDF/RoboIDF-Ecosystem) 提供显式注册的离线插件与兼容性示例。下游固定 Core Git 提交，升级时同步 Pixi 锁文件并运行回归。

参见 [当前验收状态](docs/v0.2-acceptance.md)、[项目群总览](docs/overview.md)、[贡献指南](CONTRIBUTING.md)。环境与测试通过不构成真实运动授权。Tianji/Wuji SDK、模型、标定及真机数据暂无，M2/M4 实际验收仍待完成。

[早期说明](docs/pre-m0-status.md) 仅作历史参考。论文与 Overleaf 工作已停止，原文件保留。项目许可证尚未确定。
