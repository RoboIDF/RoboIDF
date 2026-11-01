# M0 之前的历史说明

以下状态仅代表 M0 实现前，请以仓库 README 为准。

# RoboIDF — Robotics Identification Framework

更新日期：2026-11-01。状态：项目文档与 Pixi 基础环境；Harness 及硬件功能尚未实现。

[项目群总览](https://github.com/RoboIDF/RoboIDF/blob/main/docs/overview.md) · [评测项目](https://github.com/RoboIDF/RoboIDF-Bench) · [社区项目](https://github.com/RoboIDF/RoboIDF-Ecosystem)

[论文草稿入口](../papers/README.md)：v0.1 设计与实验协议初稿（2026-11-01），包含工作流、安全合同、评测计划及已核对参考资料；尚无实现或实验结果，不构成功能验证。

## 定位与边界

Open-source Agent Harness for Robot System Identification。
帮助非系统辨识专家完成机器人检查、能力分析、任务规划、实验设计、预检查、受控采集、
参数估计、诊断、主动实验迭代、独立验证和模型交付。

核心是连接 Agent、硬件、数据和已有辨识器的可复现工作流。
不以重新实现优化器为首要目标，不把专业实验决策推给 Adapter 开发者。

## 拟建模块

| 模块 | 职责 |
|---|---|
| Context / Run State | 机器人能力、任务预算、实验历史、恢复点和产物索引 |
| Skill Registry / Tools | 类型化输入输出、预检查、执行、中止和失败码 |
| Orchestrator | 任务依赖、主动实验选择、预算与终止、失败恢复 |
| Robot Interface | HardwareAdapter、RobotDescription、IdentificationProfile、Safety Profile 与装配图 |
| Safety / Executor | 人工授权、约束验证、独立监督、受控执行与停止 |
| Identification Backend API | 统一数据、参数、诊断和后端适配合同 |
| Evaluators / Artifact Registry | 数据质量、可辨识性、候选模型、独立验证和来源追溯 |

上表均为设计目标，尚无可调用实现。优先评估 MuJoCo SysID，随后按需求评估 PACE、
Isaac Sim SysID 等；版本、许可和兼容性要在实际接入时验证。

## 与其他项目的合同

- 向 Bench 暴露可重放的任务输入、运行轨迹、预算、人工干预与失败事件、候选模型和报告。
- 向 Ecosystem 提供带版本的 Adapter、机器人描述、Profile、数据和模型元数据规范。
- 接收 Ecosystem 扩展而不硬编码具体品牌；接受 Bench 的独立验收而不以 Agent 自评代替评测。
- 参数声明须区分真实物理参数与等效闭环参数；无法辨识或证据不足需明确退出或请求补充数据。

## 首个开发切片

1. 定义 M0 的最小机器人、数据、参数、实验授权和结果合同。
2. 与 Bench 共同确定合成任务、训练/验证切分及验收标准。
3. 实现无真机的 Mock Robot 和可重放任务状态机。
4. 接入一个经过验证的辨识后端，形成检查→实验→拟合→诊断→报告闭环。
5. 再接入 Wuji Hand 2、Tianji Arm 和双臂装配验证。

真机实验必须通过独立安全执行通道；未知标定不默认单位变换，设备时钟不默认已同步。

## 环境与操作

本仓库独立维护 `pixi.toml` 和 `pixi.lock`，无需父目录或其他项目即可安装。
当前仅配置 linux-64 / Python 3.12；尚未安装或验证机器人 SDK 与辨识后端。

```bash
pixi install --locked
pixi run --locked info
pixi run --locked python --version
```

在本仓库执行以上命令。通过 `pixi add <package>` 或 `pixi add --pypi <package>`
添加依赖，清单与锁文件一起提交；不提交 `.pixi/`。`info` 只展示本文，不执行辨识。

## 当前进展与维护

- 已建立：职责说明、开发顺序、项目文档及独立 Pixi 环境配置。
- 已验证（2026-11-01）（迁移前记录）：工作区环境安装成功；`info` 与本文一致；锁定环境运行 Python 3.12.16，解释器位于工作区对应环境。
- 未实现：所有上表模块、Mock 闭环、SDK 接入、辨识算法适配、模型输出及功能测试。
- 待确认：真实设备型号/固件、SDK 版本、Wuji 手数量、反馈通道语义与安装标定。
- 验证边界：本轮验证环境可创建、Python 可运行、info 可读取本文；不构成硬件或算法验证。
- 每次更新记录完成项、实际执行命令/证据和下一步；涉及接口、依赖或共同里程碑时同步根 README。

`docs/superpowers/` 中的 bootstrap 文档是早期未执行方案，定位和范围以当前文档为准。

## 仓库与发布范围

仓库：https://github.com/RoboIDF/RoboIDF 。首次提交仅包含规划文档、维护约定与 Pixi 配置。
当前未选择项目许可证；公开可见不代表已授予开源再分发许可。

2026-11-01 独立仓库验证：`pixi install` 成功，`pixi run --locked info` 与 README 一致；Python 解释器位于本仓库 `.pixi/envs/default`，仓库内文档链接检查通过。

## LaTeX 科研写作环境

见 [写作与编译说明](../paper/README.md)。使用 `pixi run --locked paper-build` 生成 LaTeX、PDF 与 Overleaf 导入包；使用 `pixi run --locked paper-check` 检查引用和输出。

2026-11-01：本地 LaTeX 编译与 PDF 检查通过；已检查全部页面排版。Overleaf 项目链接已收到，导入与同步尚未完成，具体状态见写作说明。

GitHub Actions 自动编译已启用，2026-11-01 首次运行通过：[验证记录](https://github.com/RoboIDF/RoboIDF/actions/runs/41294469162)。论文、脚本或环境变更会自动编译、检查并上传产物。Overleaf 仍待有效 Git 认证。
