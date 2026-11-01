# RoboIDF 项目群总览

更新日期：2026-11-01。当前交付为规划文档与独立 Pixi 环境，业务功能尚未实现。

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
| [RoboIDF](../README.md) | Agent Harness 与通用机器人接口 | Skills、Tools、状态管理、安全执行合同、辨识后端接入、模型产物 |
| [RoboIDF-Bench](https://github.com/RoboIDF/RoboIDF-Bench) | 独立评测与研究体系 | 合成、真实离线、Agentic、组件兼容及跨仿真器验证 |
| [RoboIDF-Ecosystem](https://github.com/RoboIDF/RoboIDF-Ecosystem) | 社区适配与资产体系 | 硬件 Adapter、机器人描述、辨识 Profile、数据集和验证模型 |

协作关系：Bench 定义验收协议 → RoboIDF 执行工作流 → Ecosystem 提供扩展 → Bench 验证扩展质量。
核心合同由 RoboIDF 维护；Bench 和 Ecosystem 消费带版本的合同，避免复制接口形成分叉。
Bench 不依赖 Agent 的自评结论判定成功；Core 不依赖某一个具体设备插件。

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


## 维护与环境

三个项目分别独立维护 Pixi 清单与锁文件，统一使用 Pixi。跨项目合同和里程碑变更时同步本文和各仓库 README；本地 IDF 总览存在时也同步更新。

当前尚未选择项目许可证。
