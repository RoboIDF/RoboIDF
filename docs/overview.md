# IDF：机器人系统辨识项目群

更新：2026-11-01。当前为软件／仿真开发版；**没有发布 v0.2**。用户要求全部 M0–M5 验收后才发布，暂无真实设备 SDK、模型、标定和数据。

## 三个独立仓库

- [RoboIDF](https://github.com/RoboIDF/RoboIDF)：数据与模型合同、离线工作流、数值辨识及验证工具。
- [RoboIDF-Bench](https://github.com/RoboIDF/RoboIDF-Bench)：独立生成和评估合成数据，维护基线对照与负面情景。
- [RoboIDF-Ecosystem](https://github.com/RoboIDF/RoboIDF-Ecosystem)：CSV离线示例、显式插件注册、兼容性证据和社区门户。

本地目录分别为 /home/current/IDF 下三个同名仓库。IDF 根不是 Git 仓库；根 Pixi 只转发任务，不代替子项目锁定环境。公开总览由 Core docs/overview.md 维护。

## 当前验收矩阵

| 里程碑 | 本次软件证据 | 未完成的完整验收 |
|---|---|---|
| M0 | 标量质量阻尼数据、拟合、独立回放与回归 | 不代表通用机器人辨识 |
| M1 | 原子持久化、固定工具调用、目录锁、中断恢复、预算和拒绝路径 | LLM Agent集成、真实硬件编排、多用户权限服务 |
| M2 | interface.v1 描述校验与硬件证据预检查；始终禁止执行 | Tianji/Wuji SDK、真机采集、标定、审批与独立停止实测 |
| M3 | SciPy有界拟合、诊断、激励选择、独立连续仿真/噪声/失配对照 | 多自由度、MuJoCo SysID/Isaac、真实数据与统计验证 |
| M4 | MJCF基础结构/USDA头检查、轨迹对齐和逐关节误差 | 真实装配模型、引擎加载、跨引擎动力学及数字孪生验收 |
| M5 | 显式内建CSV插件、版本与来源声明检查、实际回读fixture | 第三方设备接入验证、SDK与资产授权核实、社区治理和许可证 |

所有硬件和孪生报告保持 pending；文件结构成功不能替代动力学验证，来源字符串不能证明分发许可。M1预算是调用次数，SHA256是内容一致性检查而非签名或可信执行。

## 复现与贡献

在各仓库运行 `pixi install --locked`、`pixi run --locked test`、`pixi run --locked demo-all`。根目录可 `pixi run --locked demo-all` 转发三仓库任务。报告在各 artifacts/，CI运行全部测试与示例并保留JSON。Bench/Ecosystem固定Core Git提交；升级后必须同步锁文件并重新运行回归。

训练、验证、最终测试严格区分。最终测试不能反馈调参。不要提交凭据、受限资产或未经授权的真机数据；新增硬件不能通过离线示例自动升级支持等级。

[社区门户](https://roboidf-community.agile-auk-4941.chatgpt.site) 展示实际进度与GitHub协作入口。论文和Overleaf工作已暂停，原文件留档。本轮不创建 v0.2 tag 或 Release。许可证尚未确定。
