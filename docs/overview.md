# IDF：机器人系统辨识项目群

更新日期：2026-11-01。状态：M0 无真机合成闭环已实现；真实设备与 Agent 功能未实现。

本文件是三个项目的统一总纲，维护定位、职责边界、共同约定、里程碑和整体进展。
各项目的实现细节与本地进展以其 README 为准。

## 项目定位

RoboIDF — Robotics Identification Framework，是面向机器人开发者的开源 Agent Harness。
目标是让不熟悉底层动力学和系统辨识的开发者，也能在 Agent 的协助下完成机器人接入、
实验设计、受控真机采集、参数辨识、仿真模型校准和独立验证。

核心投入是工作流、上下文、Skills、类型化 Tools、任务编排、人工审批、评估器及结果追溯；
成熟辨识算法优先复用，而非从头重写优化器。Codex 是拟支持的默认 Agent，接口应允许替换。

参考平台：固定桌面 Tianji 双机械臂 + Wuji Hand 2。
具体手数量、硬件型号、固件、关节映射、SDK 兼容性和安装变换均待设备核对。

## 三个项目

| 目录与项目文档 | 职责 | 交付方向 |
|---|---|---|
| [RoboIDF](https://github.com/RoboIDF/RoboIDF) | Agent Harness 与通用机器人接口 | Skills、Tools、状态管理、安全执行合同、辨识后端接入、模型产物 |
| [RoboIDF-Bench](https://github.com/RoboIDF/RoboIDF-Bench) | 独立评测与研究体系 | 合成、真实离线、Agentic、组件兼容及跨仿真器验证 |
| [RoboIDF-Ecosystem](https://github.com/RoboIDF/RoboIDF-Ecosystem) | 社区适配与资产体系 | 硬件 Adapter、机器人描述、辨识 Profile、数据集和验证模型 |

协作关系：Bench 定义验收协议 → RoboIDF 执行工作流 → Ecosystem 提供扩展 → Bench 验证扩展质量。
核心合同由 RoboIDF 维护；Bench 和 Ecosystem 消费带版本的合同，避免复制接口形成分叉。
Bench 不依赖 Agent 的自评结论判定成功；Core 不依赖某一个具体设备插件。

## 当前目录与文档约定

```text
IDF/
├── README.md                 # 统一总纲与总体状态
├── AGENTS.md                 # 后续工作及文档同步约定
├── pixi.toml                 # 本地总览与项目任务转发入口
├── pixi.lock                 # 实际求解的可复现依赖
├── .gitignore
├── RoboIDF/
│   ├── README.md             # 主项目设计与进展
│   └── docs/superpowers/     # 保留的早期方案，已标记历史状态
├── RoboIDF-Bench/
│   └── README.md             # 评测协议与进展
└── RoboIDF-Ecosystem/
    └── README.md             # 社区适配规则与进展
```

三个目录分别为组织 `RoboIDF` 下的独立 Git 仓库：

- https://github.com/RoboIDF/RoboIDF
- https://github.com/RoboIDF/RoboIDF-Bench
- https://github.com/RoboIDF/RoboIDF-Ecosystem

IDF 根目录是本地协调工作区，不初始化为父 Git 仓库。个人仓库 `suzhelearning/RoboIDF` 不做修改。
各项目维护独立 `pixi.toml`、`pixi.lock`、`AGENTS.md` 和 `.gitignore`。
公开项目群总览位于 `RoboIDF/docs/overview.md`，跨项目决策变更时与本文同步。

## Pixi 环境管理

统一使用 Pixi，各仓库独立管理依赖与锁文件，单独克隆即可使用。
初始平台为 `linux-64`，Python 为 `3.12.*`，Pixi 要求 >=0.76.0。
后端与 SDK 的兼容性尚未确认，后续各项目按实际需求添加依赖和专用环境。

在任一项目目录执行：

```bash
pixi install --locked
pixi run --locked info
pixi run --locked python --version
```

在 IDF 根目录执行 `pixi run info` 查看总览，或 `pixi run core-info`、
`pixi run bench-info`、`pixi run ecosystem-info` 转发到对应仓库。
根环境不替代项目环境；项目依赖在项目内通过 `pixi add` 管理。
清单与锁文件一起提交，`.pixi/` 不提交。旧根目录 core/bench/ecosystem 环境已不再使用。
`info` 只显示文档，不运行辨识或评测。

## 共同工程原则

1. 机器人按 Base、Manipulator、End Effector、Body、Sensors 组件和装配关系描述；硬件适配与辨识 Profile 独立。
2. 参数区分 `IDENTIFIED`、`EFFECTIVE_ONLY`、`UNIDENTIFIABLE`、`PRIOR_ONLY`；证据不足时不得声称恢复真实物理参数。
3. 数据记录控制模式、反馈语义、设备/主机时间戳、时钟域、校准与数据切分；区分时间对齐误差和执行器物理时延。
4. Agent 通过预检查、可中止的高层实验工具访问执行器；授权、独立安全监督和停止机制不得由 Agent 绕过。
5. 原始模型、候选参数补丁、独立验证和正式发布分离；保留来源、版本、适用范围和失败记录。
6. 独立测试集不得成为 Agent 反复调参的反馈集。MJCF/USD 可加载不等于动态一致性达标。

## 联合里程碑

| 阶段 | 主交付 | 验收依据 | 状态 |
|---|---|---|---|
| M0 Specification | 机器人描述、Adapter/Safety/数据合同、评测协议 | 合同评审与 Schema 检查 | 待实现；本次仅完成组织与环境基础 |
| M1 Harness MVP | Mock Robot、Skills、Tools、运行状态与报告 | 无真机完成端到端模拟辨识 | 待实现 |
| M2 Real Hardware | Wuji Hand 2、Tianji Adapter、受控采数 | 授权边界内实验与故障处理证据 | 待实现 |
| M3 Identification | 成熟后端接入、诊断、主动实验 | 保留轨迹误差及实验效率对照 | 待实现 |
| M4 Digital Twin | MJCF/USD、装配模型、跨引擎验证 | 双臂与灵巧手独立回放验证 | 待实现 |
| M5 Open Ecosystem | 模板、贡献指南、兼容性工具 | 外部贡献者不改 Core 接入新设备 | 待实现 |

下一步先定义 M0 的最小合同和验收协议，再实现 Mock 闭环。MuJoCo SysID、PACE、Isaac Sim SysID
属于待评估集成对象；未安装、未验证兼容性，不视为当前可用能力。

## 文档维护

- 修改项目定位、跨项目接口、公共依赖或里程碑时，同步更新本文件和相关项目 README。
- 单项目实现变动首先记录在该项目 README；统一总纲只保留跨项目影响和总体状态。
- 每次记录更新日期、完成项、验证证据、待办与阻塞；“计划”不得改写为“已实现”。
- 既有早期方案保留为历史资料；冲突时以本总纲及各项目最新文档为准。
- 此处的“维护”是后续修改时同步更新，不配置无人值守定时更新。

## 依据与记录

- 用户提供的[最新总结分享链接](https://chatgpt.com/share/6ae6fd9d-d8d4-83e8-9137-d7cbfea87a37)。
  分享页正文未能直接读取；本次通过原会话 `6ae6eff1-a73c-83ee-82ee-a5cc8b0f92dd`
  读取最新总结，其中明确划分上述三个项目。本文据此整理，新增环境约定是本次工程选择。
- [Pixi 清单文档](https://pixi.prefix.dev/latest/reference/pixi_manifest/)。
- 2026-11-01：建立三个项目入口、统一文档和 Pixi 环境；业务代码、真机支持、Benchmark 成绩与开源许可证尚未交付。
- 2026-11-01 验证：`pixi install --all` 成功创建四个环境并生成 `pixi.lock`；
  四个环境的 `pixi run --locked -e <环境> info` 输出与对应 README 一致，Python 均为 3.12.16，
  各解释器位于独立 `.pixi/envs/<环境>`。16 个本地文档链接全部有效。

- 2026-11-01 发布：三个项目已分别推送到 RoboIDF 组织公开仓库的 main，origin/main 跟踪已配置。逐仓库核对远程 SHA 与本地一致、工作区干净，并完成全新克隆的 `pixi install --locked` 和 `pixi run --locked info` 验证。根任务转发检查通过。

## 论文与社区门户（2026-11-01）

- RoboIDF/papers/roboidf-draft.md：系统架构与执行合同的设计/协议初稿。
- RoboIDF-Bench/papers/roboidf-bench-draft.md：四类评测与公平对照协议初稿。
- 社区门户：https://roboidf-community.agile-auk-4941.chatgpt.site ，Sites 公开发布成功。
- 源码位于 RoboIDF-Ecosystem/website/dist；通过 `pixi run website` 本地预览。
- 网站首版采用项目门户与 GitHub 协作入口，不提供站内账号与上传。两篇论文的实验结果均未采集；不改变业务模块尚未实现的状态。

## 科研写作环境（2026-11-01）

RoboIDF 与 RoboIDF-Bench 的活动论文源迁至各自 `paper/manuscript.md`，旧 `papers/` 保留为历史初稿。各自 Pixi 锁定 Pandoc、Tectonic 与 PyMuPDF，提供 `paper-build`、`paper-check`。LaTeX、PDF、引用与 Overleaf 导入包已生成并检查（分别 8 页和 10 页）；Overleaf 编辑器控制超时，导入、在线编译和 Git 同步待完成。

2026-11-01：Core 与 Bench 的 GitHub Actions 自动编译均已启用并成功执行，编译、检查与产物上传通过。Overleaf 浏览器控制不可用，Git 认证失败，源码尚未上传。

## 当前 M0 交付

以用户最新批准的无真机闭环为准，取代早期 M0/M1 的占位划分：Core 提供数据合同、合成质量阻尼模型、拟合与回放；Bench 提供三组独立合成验收及负面对照；Ecosystem 提供 CSV 离线适配示例。各目录均可运行 `pixi run --locked test` 和 `pixi run --locked demo`。Bench/Ecosystem 固定 Core Git 提交，无父目录路径依赖。报告保存在各仓库 artifacts/。

论文工作与 Overleaf 接入已停止，既有文稿留档。社区文档与代码同步维护；线上门户尚未重新部署。M0 不提供真机安全执行、Agent 或数字孪生验证。
