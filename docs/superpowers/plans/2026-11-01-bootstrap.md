# RoboIDF Bootstrap Implementation Plan

> 已被 2026-11-01 三项目组织方案替代，保留为历史记录，不再执行本计划。
> 当前范围和状态见 [IDF 总纲](../../overview.md) 及 [RoboIDF 当前文档](../../../README.md)。

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** 在项目目录建立可安装的 RoboIDF 初始工程并首次推送 GitHub。

**Architecture:** 核心包只定义类型和协议；硬件、算法和仿真实现保留为后续扩展。文档明确现有能力与路线图。

**Tech Stack:** Python >=3.10、setuptools、标准库。

**Spec:** `docs/superpowers/specs/2026-11-01-bootstrap-design.md`

## Global Constraints

- 不混入当前聊天文件或其他项目文件。
- 不执行真实机器人运动；不宣称已经完成驱动和辨识。
- 远程为空才首次推送，禁止强制推送。

## Review Focus

安装后可导入；接口不暗含真实控制；示例无虚构标定；文档无不存在的命令；提交无本地环境和秘密。

## Task 1: 初始工程

Files: `pyproject.toml`, `src/roboidf/{__init__,contracts}.py`, `README.md`, `LICENSE`, `.gitignore`, `CONTRIBUTING.md`, `docs/{architecture,adapting,benchmark}.md`, `examples/tianji_wuji.template.json`.

Interfaces: `Capabilities`, `StampedState`, `RobotDescription`, `HardwareAdapter`, `IdentificationProfile`, `SimulationBackend`，全部为数据结构或静态协议。

- [ ] 编写包元数据、协议草案、文档与示例；不新增运行时业务行为。
- [ ] 在独立临时环境安装包，从项目外导入，检查示例 JSON 与协议类型。
- [ ] 审查 Git 文件清单和 diff，确认没有缓存、凭据或未实现功能的成功声明。
- [ ] 配置 origin 和 main，确认远程仍为空后非强制 push，并核对远程 SHA 和 upstream。
