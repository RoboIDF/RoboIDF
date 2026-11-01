# RoboIDF 初始工程范围

> 历史草案，未按本文实现。2026-11-01 最新方案已将项目定位更新为 Agent Harness，
> 并划分为三个项目、统一使用 Pixi。以 [IDF 总纲](../../overview.md)
> 和 [RoboIDF 当前文档](../../../README.md) 为准；本文中的许可证和包交付均未完成。

基于已有 RoboIDF 讨论及本次创建初始工程、推送 GitHub 的任务。

RoboIDF（Composable Robot Identification Framework）面向可组合机器人系统辨识。
参考平台为固定桌面 Tianji 双臂与 Wuji Hand 2；具体手的数量、关节、固件和安装变换尚待核对。

## 方案与取舍

仅建 README 无法展示扩展边界；直接实现完整算法与硬件控制超出首次初始化范围。
本次采用轻量 Python 工程骨架，描述 HardwareAdapter、RobotDescription、
IdentificationProfile、SimulationBackend 四类扩展，保留后续实现空间。
这是执行时的范围选择，不代表已经验证硬件兼容性。

## 初始交付

- Python >=3.10、src 布局、无运行时第三方依赖。
- 核心数据类型和接口草案，不提供运动执行入口。
- JSON 示例装配描述，未知安装变换保持 null，不填造测量值。
- README、适配指南、Benchmark 规划、贡献说明和 MIT 许可证。
- 实际验证安装、导入、示例语法与提交文件清单。

硬件控制、实验执行、参数辨识、仿真导出、插件自动发现及性能基准均不属于本次交付。
接口为实验性草案，尚未承诺稳定性；后续真实实验必须独立设计并验证安全边界。
