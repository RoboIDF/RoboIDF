# M2 / M4 离线接口与回放检查

实现入口为 `roboidf.validation`，合同版本为 `interface.v1`，底层离线 Dataset 合同仍为 `m0.v1`。本工具不加载机器人 SDK、不连接设备、不发送运动命令，不能签发或替代真实审批。所有报告的 `hardware_status` 和 `twin_status` 始终为 `pending`，`execution_authorized` 始终为 `false`。

## 可复现演示

在 Core 仓库根目录执行：

```bash
pixi run --locked python -m roboidf.validation
pixi run --locked python -m roboidf.validation --hardware
pixi run --locked python -m unittest discover -s tests -p test_validation.py -v
```

第一个命令验证内建合成描述及三点速度轨迹，退出 0。第二个命令展示硬件拒绝，退出 1；这是预期拒绝，不应改为成功退出。也可用 `--contract path/to/contract.json` 检查外部合同。CLI 输出严格 JSON；非法输入或未通过返回非零。没有随机过程的三点演示明确标注 deterministic。

## 机器人及 Adapter 元数据合同

`example_contract()` 返回完整示例。必需字段及限制：

| 字段 | 含义与限制 |
| --- | --- |
| schema_version | 必须为 interface.v1，未知版本拒绝 |
| id | 非空标识 |
| mode / authorization | offline 配 offline-only；hardware 配 pending |
| source | uri、license、provenance 均为非空字符串；记录声明，不证明授权或许可证真实有效 |
| clock | unit=s、domain=monotonic；上游必须说明并完成真实时钟同步 |
| joints | 非空列表、唯一非空 name，type 为 prismatic 或 revolute |
| joint 单位 | prismatic：m、m/s、N；revolute：rad、rad/s、N*m |
| adapter | schema_version=interface.v1、dataset_version=m0.v1；离线 kind=offline-csv，硬件 kind=hardware-pending |

校验成功只表示元数据字段符合合同。机器人型号、动力学、实际自由度和设备能力没有得到认证。`validate_contract` 不读资产、不运行插件；输入哈希记录规范排序 JSON（Python json 默认编码）的 SHA-256。

`hardware_precheck(contract)` 检查 `hardware_evidence` 的 sdk、calibration、approval、stop 四个非空证据引用，报告缺失项。即使四项齐全，仍拒绝执行：引用没有被验证，工具没有硬件执行能力。审批、标定有效性、独立停止机制及设备支持必须由未来独立集成验收；不得用本工具输出升级状态。

## 资产结构检查边界

`validate_asset(text, kind, source)` 接受文本和来源声明：

- mjcf：解析 XML，要求 mujoco 根和 worldbody，拒绝 DTD、实体声明和 include。这里只检查基本树结构，不是完整 MJCF schema 校验；不启动 MuJoCo，不检查网格、惯量、接触或动力学。
- usd：只接受首行为 `#usda 1.0` 的文本，报告 scope=header-only。不会解析 USD 场景图，不支持二进制 USDC，不启动 Isaac。

报告包含文本字节哈希和来源声明哈希。Ecosystem `examples/synthetic-structure-v1.xml`、`synthetic-header-v1.usda` 及 `asset-structure-evidence-v1.json` 是实际执行此检查产生的合成示例。结构成功不能解释为引擎可加载或跨引擎一致。

## 回放动态误差

`compare_replay(reference, replay, rmse_limit=...)` 比较两段已生成的速度序列，并不运行物理引擎。输入见 `example_trajectory()`：版本、source、time_unit、clock_domain、time、joint_names、velocity_units、velocity 矩阵。

时间必须有限且严格递增；两段 time 数组、关节顺序、单位、时钟域必须精确一致。工具不会暗中插值、时间平移、重排关节或转换单位。CSV 的均匀采样要求属于既有 Adapter；这里允许共同的不均匀时间轴。所有数值必须有限，矩阵形状必须匹配。报告逐关节 RMSE 和最大绝对误差；每个关节 RMSE 均不超过阈值才 passed=true。阈值按各关节声明单位解释，混合单位时调用者应预先选择合理阈值；不把不同单位混合计算成一个物理指标。

报告记录两段输入哈希、阈值和 exact 对齐策略。样本 RMSE 包含初始样本、按样本等权，不是时间积分误差。Ecosystem 的三点候选在中点引入 0.03 m/s 偏差，RMSE 约 0.01732 m/s，在 0.01 阈值下明确失败；这是阈值拒绝的证据，不是训练或真实回放数据。

## 已覆盖测试与未实现内容

测试包含非法版本、缺来源、授权误用、时钟及关节单位不匹配、重复关节、结构错误、轨迹错位、NaN、阈值超限和 CLI 硬件拒绝。当前没有 SDK、真实标定、审批服务、停止执行器、Tianji Arm / Wuji Hand 2 驱动或 MuJoCo / Isaac 动态回放集成，M2/M4 真机与孪生验收仍 pending。

CLI 默认同时写入 `artifacts/validation.json`，可用 `--output path/to/report.json` 指定保存位置。拒绝与非法业务输入也保存结构化报告；写入失败会非零退出。重复运行会覆盖同一报告，CI 应在测试后运行所需演示或为不同场景设置独立输出名。
