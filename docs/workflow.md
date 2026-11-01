# M1 可恢复离线工作流

`roboidf.workflow` 将现有 `MockRobot → fit → rollout_rmse` 封装为三个固定步骤：`collect`、`fit`、`validate`。只处理合成离散单自由度质量阻尼系统，不是自主 Agent、安全执行器或真机驱动。所有运行的 `hardware_status` 都是 `pending`。

## 中断与恢复

在仓库根目录运行：

```bash
pixi run python -m roboidf.workflow --output artifacts/workflow --stop-after 1
# 预期退出码 3；collect 已完成并落盘。
pixi run python -m roboidf.workflow --output artifacts/workflow
# 预期退出码 0；跳过 collect，完成 fit、validate，总 attempts 为 3。
```

再次执行第二条命令读取相同成功状态，不重新执行工具。CLI 标准输出为严格 JSON 摘要；完整输入数据、模型、验证误差、配置、输入哈希及失败记录保存在输出目录 `state.json`。`validation` 使用 `seed + 1`，训练只接受 `train`；本模块没有最终测试集调参入口。

`--stop-after N` 在本次调用完成 N 个步骤后主动中断（全部完成则仍成功）。进程在某步骤执行中退出时，磁盘保留该步骤 `running`；下次调用重试这个未确认完成的步骤。已完成且落盘的步骤不重跑。工具执行完但结果尚未落盘的窗口无法保证恰好一次；内置工具无外部副作用，可安全重算，重试仍消耗预算。

## Python 接口

```python
from roboidf.workflow import WorkflowConfig, run

config = WorkflowConfig(seed=42, samples=500, dt=.02, max_calls=6,
                        offline_approved=True, validation_tolerance=1e-8)
state = run('artifacts/workflow-python', config, stop_after=1)
state = run('artifacts/workflow-python', config)
```

- `WorkflowConfig`：冻结配置，运行时检查整数、布尔值、数值范围与有限性。
- `ToolRequest(tool: str, arguments: dict)`：显式请求类型；工具名称只允许上述三个内置值。参数在分发时按工具签名、配置或已有数据合同校验。
- `ToolRegistry`：显式注册固定内置工具，重复注册与未知名称拒绝。不支持加载任意模块、动态路径、命令或外部插件；不执行状态文件中的代码。
- `run(output, config=None, *, stop_after=None, terminate=False)`：返回运行状态；坏输入、坏状态、不同配置、目录忙时报 `WorkflowError`（`ValueError` 子类）。工具执行失败则保存 `failed` 和错误文字并返回状态，不冒充成功。
- `directory_lock(output)`：Linux `flock` 非阻塞互斥；同目录并发立即拒绝。进程退出后锁自动释放，无需删除锁文件。

## 审批、预算与终止

默认配置中的 `offline_approved=True` 仅表示允许本地合成运算。设置 `False` 或 CLI `--deny-offline` 会在执行前得到 `approval_required`，工具调用数为零。它不能授权硬件，未知或 `hardware.move` 请求一律拒绝。真实设备审批不在这个模块内。

`max_calls` 限制整个运行的工具尝试次数，每次执行前先增加并持久化。崩溃后的重试也计数；预算耗尽后不执行更多工具。它不是 CPU 时间、内存、费用或进程隔离限制。输入样本数范围为 3–100000。

`run(..., terminate=True)` 或 CLI `--terminate` 写入 `terminated`。失败、审批缺失、预算耗尽、终止和成功均为终态，后续调用读取原状态；不自动重试已记录的失败。变更配置（包括增加预算或改变审批）必须选一个新的输出目录，不可悄悄继承旧成功。终止请求若目录正被占用会拒绝，不会强杀另一个进程。

| 退出码 | 含义 |
| --- | --- |
| 0 | 成功 |
| 1 | 工具失败，失败原因已保存 |
| 2 | 输入、状态、配置或并发锁拒绝；也用于命令行参数错误 |
| 3 | 主动中断，可恢复 |
| 4 | 缺少离线批准 |
| 5 | 持久化调用预算耗尽 |
| 6 | 已终止 |

## 持久化与信任边界

状态版本为 `workflow.v1`。保存使用同目录临时文件、文件 `fsync`、原子替换及目录 `fsync`。读取有 32 MB 大小上限，拒绝非有限 JSON 数值、重复键、错误字段、未知状态/步骤、错误顺序、不一致终态、配置或数据哈希不匹配，并重新构造 `Dataset`/`Parameters` 验证基本物理合同。每步请求含 `input_sha256`，配置含 `config_sha256`，整个状态含 `state_sha256`。

这些普通 SHA-256 校验用于发现损坏与输入混淆，不是签名或授权凭证；能修改状态并重新计算所有哈希的人仍能伪造结构合法的结果。恢复不会重新执行已完成的拟合来证明其科学真实性。只在可信本地输出目录使用，不能把来自他人的状态当成认证结果。锁是协作式本地锁，不保证网络文件系统、非协作写入者或恶意目录替换的行为。该版本不提供状态迁移；变更工具语义应升级合同版本并拒绝旧状态。

## 验证

```bash
pixi run python -m unittest discover -s tests -p test_workflow.py -v
```

专项测试覆盖正常恢复、步骤执行中断、已完成步骤不重跑、配置改变、失败记录、预算、终止、离线审批、并发目录、结构损坏、数据篡改、更新校验和后的不一致状态、重复 JSON 键、非法工具和 CLI 退出码。
