# DBS 脑电采集电极要求调研（加强版）

调研日期：2026-06-10  
适用范围：深部脑刺激（deep brain stimulation, DBS）系统中的局部场电位（local field potential, LFP）采集电极，尤其是可感知 DBS、闭环 DBS、刺激-记录共用触点，以及动物或临床植入式深部脑区记录。  
版本说明：本版保留上一版的整体框架，但重点加强第 4-7 章：电极阻抗、表面/界面敏感性、电荷密度/刺激安全、刺激伪迹与采集前端。新增更多数据、计算示例和验收口径。

## 1. 核心结论

DBS 脑电采集电极的要求不是头皮 EEG 电极要求的简单延伸。头皮 EEG 关注“电极-皮肤”界面，而 DBS/LFP 关注“植入电极-脑组织/脑脊液”界面；因此头皮 EEG 常见的 `≤5 kΩ` 皮肤电极阻抗经验不能直接套用到 DBS。DBS 采集电极要同时满足三件事：长期植入稳定、刺激安全、刺激打开时仍能采到可用 LFP。<sup>[10][11][13][18]</sup>

对 DBS 项目而言，最重要的指标组合是：

| 目标 | 关键指标 | 为什么重要 |
|---|---|---|
| 可记录 | 记录阻抗、输入噪声、LFP 频段信噪比 | LFP 振幅通常远小于刺激伪迹，阻抗和前端噪声会直接影响可用信号。<sup>[5][6][9]</sup> |
| 可刺激 | 治疗阻抗、电压顺应性、每相电荷、电荷密度 | 同一触点常承担刺激，必须避免过高电压、不可逆电化学反应和组织损伤。<sup>[10][11][13][14]</sup> |
| 可长期用 | 阻抗漂移、材料腐蚀、胶质包裹、涂层稳定性 | 慢性植入后电极-组织界面会变化；Satzer 等报道 DBS 阻抗多年随访中平均下降约 `73 Ω/year`，激活触点平均低约 `163 Ω`。<sup>[12]</sup> |
| 可闭环 | 刺激伪迹耐受、blanking、刺激后恢复时间 | 闭环 DBS 需要在刺激开/关和刺激后短时间内可靠估计 biomarker。<sup>[6][7][8]</sup> |

## 2. 基础概念

### 2.1 LFP 和头皮 EEG 的区别

LFP 是植入电极在深部脑区记录到的局部群体神经活动，常见 DBS 靶点包括 STN、GPi、VIM、丘脑、NAc 等。临床和闭环 DBS 中常关注 `1-500 Hz` 范围内的信号，其中帕金森病常用 beta 频段约 `13-30 Hz`，也会分析 gamma、震颤频段、刺激诱发响应等。<sup>[1][3][4][6]</sup>

头皮 EEG 是远场信号，受皮肤、头骨、肌电和眼电影响；DBS-LFP 是近场植入信号，但会强烈受刺激伪迹、电极极化、导线耦合和组织反应影响。因此二者共享“电极阻抗、噪声、极化”这些概念，但不能共享阻抗阈值和验收方法。

### 2.2 电极-组织界面

DBS 电极触点通常为金属或导电涂层，与脑脊液、细胞外液、蛋白、细胞和胶质组织接触。界面可以粗略理解为：金属电子导体和组织离子导体之间的转换层。这个界面决定了阻抗、双电层电容、极化、电荷注入能力、刺激后恢复时间和慢性稳定性。<sup>[10][11][14]</sup>

### 2.3 记录阻抗和治疗阻抗

- 记录/电化学阻抗：通常用 EIS 测量，小信号、频率扫描，常报告 `1 kHz` 阻抗和相位。它更接近电极-组织界面的记录噪声、极化和电化学状态。<sup>[10][14][16]</sup>
- 治疗阻抗：由 DBS 设备用刺激脉冲或测试脉冲估算，包含触点、组织、导线、连接器和 IPG 输出路径。它更适合判断开路、短路、连接异常和刺激功耗。<sup>[12][15][19]</sup>

### 2.4 CSC、CIC 和电压瞬态

CSC 通常来自循环伏安（CV），表示电极在给定电位窗口和扫描速率下可存储/释放的电荷。CIC 更接近刺激安全，表示电极在不越过安全电位窗口时能注入的电荷。Harris 等指出，CSC 高度依赖测试方法、几何结构和表面状态，不能只比较一个孤立数字。<sup>[10]</sup>

对 DBS 来说，CIC、电压瞬态和每相电荷密度通常比单独的 CSC 更关键，因为 DBS 是脉冲刺激场景，真正需要确认的是刺激脉冲后电极电位是否越过水窗、是否产生不可逆反应，以及多快恢复到可记录状态。<sup>[10][13][14]</sup>

## 3. 电极形态

| 电极形态 | 典型用途 | 阻抗量级怎么理解 | 设计重点 |
|---|---|---|---|
| 临床 DBS 宏触点 | 长期刺激 + LFP 采集 | 治疗阻抗常在数百到数千 Ω量级；工程上常把约 `500-2000 Ω` 作为常见工作区间，但实际阈值以厂家和测试模式为准。<sup>[12][19][20][21]</sup> | 长期稳定、低功耗、低刺激伪迹、足够安全电荷注入 |
| 分段 DBS 触点 | 定向刺激 + 多触点感知 | 单个分段面积小于完整环形触点，同样电流下电荷密度更高，阻抗和边缘电流密度更敏感。<sup>[13][17][23][25]</sup> | 方向性、触点间一致性、局部电荷密度、安全余量 |
| 深部微电极/微阵列 | 动物实验、单位放电、局部高分辨记录 | 1 kHz 阻抗可达到几十 kΩ到 MΩ量级，取决于几何面积和涂层；不能与 DBS 宏触点数百 Ω到低 kΩ量级混用。<sup>[22][24][26]</sup> | 高空间分辨、低噪声、材料涂层、组织反应 |
| 涂层/改性电极 | 降阻抗、提高 CSC/CIC、改善伪迹恢复 | IrOx、TiN、PEDOT 等可提高有效面积和电容、降低界面阻抗，但老化和脱层风险必须验证。<sup>[14][23][24][26]</sup> | 涂层附着、长期浸泡、脉冲耐久、生物相容性 |

## 4. 电极阻抗要求（加强）

### 4.1 阻抗的三层含义

DBS 项目里建议把阻抗拆成三层管理：

| 阻抗类型 | 常见测试 | 主要用途 | 易混点 |
|---|---|---|---|
| 电化学阻抗 | EIS，小信号 `1 Hz-100 kHz`，常看 `1 kHz` | 材料/界面表征、记录噪声、极化趋势 | 不是 DBS 设备显示的治疗阻抗 |
| 治疗阻抗 | IPG 或外部刺激器测试脉冲 | 判断短路、开路、连接异常、功耗 | 包含组织、导线、连接器和输出路径 |
| 有效工作阻抗 | 实际刺激波形下的电压/电流关系 | 估算顺应电压、功耗、电场 | 会随脉宽、电流、频率、组织状态变化 |

体外 EIS 建议使用 PBS 或人工脑脊液、`37°C`、`1 Hz-100 kHz`、`5-10 mV` 小信号幅度，并报告幅值与相位。至少给出 `1 Hz`、`10 Hz`、`100 Hz`、`1 kHz`、`10 kHz` 这些频点，而不是只给单个 `1 kHz` 数值。EIS 是植入电极界面表征的基础方法。<sup>[10][14][16]</sup>

### 4.2 临床 DBS 宏触点的阻抗量级

临床 DBS 宏触点的治疗阻抗通常为数百到数千 Ω量级。工程调研中可把约 `500-2000 Ω` 作为常见工作区间，但异常阈值必须按具体设备和测试模式定义。<sup>[12][19][20][21]</sup>

更可操作的验收口径如下：

| 场景 | 建议关注 | 数据/判断 |
|---|---|---|
| 植入/连接完整性 | 是否出现异常高阻或低阻 | 高阻可能来自开路、连接异常、触点周围气体/液体状态；低阻可能来自短路或绝缘问题。Lyons 等报道术中高阻可由颅内气体包绕触点导致。<sup>[15]</sup> |
| 慢性随访 | 阻抗随时间变化 | Satzer 等在 `84` 名患者、`128` 根 DBS 电极中发现阻抗平均下降约 `73 Ω/year`，`72%` 触点呈下降趋势，激活触点平均低约 `163 Ω`。<sup>[12]</sup> |
| 触点选择 | 相邻触点一致性 | 同一导线相邻触点阻抗差异过大时，双极 LFP、方向性刺激和闭环特征比较会变复杂。<sup>[1][3][12]</sup> |
| 电流递送 | 阻抗对刺激场影响 | Butson 等指出 DBS 电极阻抗来源会影响电流递送和刺激组织体积估算。<sup>[19]</sup> |

### 4.3 不同电极形态的建议阻抗数据

| 电极形态 | 记录/测试阻抗建议 | 解释 |
|---|---:|---|
| 临床环形宏触点 | 治疗阻抗常见约 `500-2000 Ω`；EIS 的 `1 kHz` 阻抗通常应处于低 kΩ 或以下量级。<sup>[12][19][20][21]</sup> | 宏触点面积大，阻抗低，适合刺激和 LFP。 |
| 分段触点 | 不要求等于环形触点，但每个分段触点应单独建档，重点看触点间一致性和电荷密度。<sup>[13][17][23][25]</sup> | 面积小，局部电流密度高。 |
| 深部微电极 | `1 kHz` 可为几十 kΩ到 MΩ量级。<sup>[22][24][26]</sup> | 面积小，换取空间分辨率；不能按宏触点低阻抗要求验收。 |
| 涂层微电极/改性触点 | 目标通常是相对未涂层显著降阻抗、提高相位电容特征；必须报告老化前后变化。<sup>[14][23][24][26]</sup> | 初始低阻抗不等于慢性稳定。 |

### 4.4 阻抗和热噪声的量级估算

电极-前端等效阻抗越高，热噪声越高。按 Johnson 噪声公式估算，在 `37°C`、`500 Hz` 带宽下，纯电阻热噪声量级如下；这是计算值，用于说明阻抗量级对低噪声采集的影响，实际噪声还包括前端、电极极化和环境耦合。<sup>[14][20][21][26]</sup>

| 等效阻抗 | `500 Hz` 带宽下热噪声估算 |
|---:|---:|
| `1 kΩ` | 约 `0.09 µV rms` |
| `10 kΩ` | 约 `0.29 µV rms` |
| `100 kΩ` | 约 `0.93 µV rms` |
| `1 MΩ` | 约 `2.9 µV rms` |

这也是为什么 DBS 宏触点的低阻抗对 LFP 采集有利，而微电极系统必须更重视低噪声前端、屏蔽、参考设计和涂层。

### 4.5 建议的阻抗数据记录模板

每根导线/每个触点建议记录：

| 项目 | 记录内容 |
|---|---|
| 几何信息 | 触点类型、触点长度/宽度/面积、环形或分段、材料/涂层 |
| 体外 EIS | `1 Hz-100 kHz` 幅值和相位，至少列 `1/10/100/1000/10000 Hz` |
| 治疗阻抗 | IPG/外部刺激器测试结果、测试模式、电压/电流参数 |
| 植入时间点 | 术中、术后初次开机、1 周、1 月、3 月、6 月、年度随访 |
| 刺激状态 | 触点是否激活、刺激电流/电压、脉宽、频率 |
| 异常说明 | 高阻/低阻复测、影像学、连接器、导线完整性、气体/水肿等解释 |

## 5. 表面/界面敏感性（加强）

### 5.1 DBS 表面敏感性的定义

DBS 电极的“表面敏感性”不是指皮肤汗液或头发，而是指电极表面对脑组织、脑脊液、蛋白、细胞、氧化还原环境和长期微动的敏感程度。它最终表现为阻抗变化、极化变化、刺激阈值变化、LFP 幅值漂移、刺激后恢复变慢或材料失效。<sup>[10][11][12][14]</sup>

### 5.2 主要界面因素及量化指标

| 界面因素 | 对采集/刺激的影响 | 建议量化指标 | 参考依据 |
|---|---|---|---|
| 蛋白吸附 | 有效面积下降、阻抗上升，CSC/CIC 下降 | 蛋白浸泡前后的阻抗模值、CSC、CIC、OCP 漂移 | 蛋白吸附和细胞生长可改变双相电极阻抗。<sup>[22]</sup> |
| 胶质包裹/炎症 | 慢性阻抗变化，刺激场和 LFP 幅值改变 | 多时间点治疗阻抗、EIS、PSD 稳定性 | 慢性 DBS 阻抗平均下降约 `73 Ω/year`；异物反应/胶质反应是侵入式神经电极的核心界面问题。<sup>[12][24]</sup> |
| 表面氧化还原 | 改变伪电容、极化和刺激后恢复 | CV 峰、电压瞬态、EIS 相位 | Pt 电极电荷注入机制和电压瞬态可用 chronopotentiometry 更好表征。<sup>[23]</sup> |
| 涂层脱落 | 阻抗回升、颗粒风险、长期可靠性下降 | SEM、附着力、老化后 EIS/CV | 材料/涂层长期稳定性和生物反应是侵入式神经电极关键约束。<sup>[14][24]</sup> |
| 微动/机械失配 | 局部组织损伤、低频伪迹、慢性炎症 | 动物组织学、低频噪声、阻抗波动 | 机械失配和异物反应是慢性植入电极失效的重要因素。<sup>[24]</sup> |

### 5.3 材料和涂层的典型电化学特征

下表是文献中的常见量级，用于材料选型阶段判断方向；实际项目必须按同一测试体系重测，不能把不同文献的 CSC/CIC 直接横向比较。<sup>[10][14]</sup>

| 材料/表面 | 典型优势 | 典型风险 | 数据口径 |
|---|---|---|---|
| PtIr | 临床 DBS 使用经验丰富，机械和化学稳定性好 | 电容/CSC 不如高表面积涂层 | 适合长期宏触点；阻抗主要由几何面积和组织界面决定。<sup>[14][19]</sup> |
| IrOx | 伪电容高，CIC/CSC 通常优于光滑 Pt 类表面 | 需要验证还原/氧化循环稳定性 | 适合刺激电极涂层研究。<sup>[14]</sup> |
| TiN | 高表面积、低阻抗、常用于神经记录电极 | 涂层附着和颗粒风险需验证 | 常用于降低小电极阻抗。<sup>[14]</sup> |
| PEDOT/PEDOT 复合 | 阻抗低、柔性好、可提高电容 | 慢性脱层、膨胀、老化和生物稳定性风险 | 新材料需做长期浸泡和脉冲耐久。<sup>[11][14]</sup> |

### 5.4 建议的表面/界面测试矩阵

| 测试阶段 | 测试内容 | 判据 |
|---|---|---|
| 初始体外 | EIS、CV、CSC、OCP、表面形貌 | 建立基线，给出均值、标准差、批次差异 |
| 蛋白污染 | 白蛋白/血清蛋白浸泡后 EIS/CV | 阻抗增幅、CSC/CIC 降幅可接受且可解释 |
| 加速老化 | `37-60°C` 人工 CSF/PBS 浸泡，周期复测 | 无明显涂层脱落、阻抗突变或 OCP 大漂移 |
| 脉冲耐久 | DBS 类双相脉冲长时间刺激 | 电压瞬态不越界，EIS/CV 不显著劣化 |
| 机械疲劳 | 弯折、扭转、连接器拉扯、涂层附着 | 无裂纹、脱层、绝缘泄漏 |
| 慢性体内 | 组织学、阻抗、LFP PSD、可用通道率 | 证明植入环境下长期稳定 |

## 6. 电荷密度与刺激安全（加强）

### 6.1 必须区分四个量

| 量 | 公式/单位 | 用途 |
|---|---|---|
| 每相电荷 `Q` | `Q = I × PW`，单位 `µC/phase` | 判断单个刺激相注入多少电荷。<sup>[13][17][23]</sup> |
| 每相电荷密度 `D` | `D = Q / A`，单位 `µC/cm²/phase` | 与组织安全和电极面积直接相关。<sup>[13][17][23]</sup> |
| CSC | CV 电流-时间积分，常归一化为 `mC/cm²` | 表征材料在给定电位窗口内的可逆/准可逆电荷存储能力，常用于比较 Pt、IrOx、TiN、PEDOT 等材料表面。<sup>[10][14][23]</sup> |
| CIC | 脉冲条件下安全注入能力，单位 `µC/cm²/phase` | 更接近 DBS 脉冲刺激安全，需结合电压瞬态和水窗判断。<sup>[14][22][23]</sup> |

Merrill、Cogan 和 Shannon 的经典文献都强调，刺激安全不能只看电流或电压，必须同时看电荷、面积、波形、电位窗口和组织反应。<sup>[13][14][17]</sup>

CSC 的关键文献口径是：Cogan 2008 将 CSC 作为神经刺激/记录电极的重要电化学表征量，通常由循环伏安（CV）曲线在限定电位窗口内积分得到，用来描述电极表面能以双电层电容或可逆氧化还原反应方式存储多少电荷。<sup>[14]</sup> Harris 等 2021 进一步指出，CSC、EIS 和有效电极面积之间有关联，但 CSC 对 CV 扫描范围、扫描速率、几何面积/有效面积和表面状态非常敏感，因此不同论文给出的 CSC 数字不能脱离测试条件直接横向比较。<sup>[10]</sup>

因此在 DBS 电极验收中，CSC 更适合回答“这个材料/涂层是否具备更高的界面电荷缓冲能力”，不应单独作为“最大安全刺激电荷”。真正贴近 DBS 刺激安全的是 CIC、电压瞬态、每相电荷密度和长期脉冲耐久的组合判断。<sup>[11][13][14]</sup>

### 6.2 宏触点与分段触点的电荷密度对比

以下用两个面积做示例：

- 宏触点面积：`0.06 cm²`，接近常见圆柱 DBS 触点尺寸折算量级。
- 分段触点面积：`0.02 cm²`，用于模拟面积约为宏触点 `1/3` 的情况。

实际项目必须替换为所用导线触点的真实几何面积或有效面积；电极几何和组织阻抗会共同影响刺激电流分布。<sup>[13][14][19]</sup>

| 刺激参数 | 每相电荷 `Q` | `A = 0.06 cm²` 时电荷密度 | `A = 0.02 cm²` 时电荷密度 |
|---|---:|---:|---:|
| `1 mA × 60 µs` | `0.06 µC` | `1 µC/cm²/phase` | `3 µC/cm²/phase` |
| `3 mA × 90 µs` | `0.27 µC` | `4.5 µC/cm²/phase` | `13.5 µC/cm²/phase` |
| `5 mA × 120 µs` | `0.60 µC` | `10 µC/cm²/phase` | `30 µC/cm²/phase` |
| `10 mA × 120 µs` | `1.20 µC` | `20 µC/cm²/phase` | `60 µC/cm²/phase` |

这张表的重点是：分段触点面积变小后，同样刺激参数下电荷密度按面积反比上升。`5 mA × 120 µs` 在 `0.06 cm²` 宏触点上约为 `10 µC/cm²/phase`，但在 `0.02 cm²` 分段触点上约为 `30 µC/cm²/phase`。<sup>[13][14][19]</sup>

### 6.3 Shannon 模型示例

Shannon 模型常写作：

```text
k = log10(D) + log10(Q)
```

其中 `D` 是每相电荷密度（`µC/cm²/phase`），`Q` 是每相电荷（`µC/phase`）。该模型是经验安全边界，不是充分安全证明；不同材料、波形和组织条件仍需单独验证。<sup>[17]</sup>

| 示例 | `Q` | `D` | `k = log10(D)+log10(Q)` | 解读 |
|---|---:|---:|---:|---|
| `5 mA × 120 µs`，`A=0.06 cm²` | `0.60 µC` | `10` | 约 `0.78` | 离常用经验边界较远 |
| `5 mA × 120 µs`，`A=0.02 cm²` | `0.60 µC` | `30` | 约 `1.26` | 分段触点安全余量明显下降 |
| `10 mA × 120 µs`，`A=0.06 cm²` | `1.20 µC` | `20` | 约 `1.38` | 宏触点下仍需结合材料和电压瞬态 |
| `10 mA × 120 µs`，`A=0.02 cm²` | `1.20 µC` | `60` | 约 `1.86` | 已接近/超过常用 Shannon 经验边界 `k≈1.85` |

这说明方向性 DBS、分段触点、小面积触点或高电流刺激不能只看电流大小，必须同步计算每相电荷密度和 Shannon 指标，并结合电压瞬态/CIC 验证。<sup>[13][14][17]</sup>

### 6.4 安全验证建议

| 验证项 | 建议数据 |
|---|---|
| 每相电荷 | 所有刺激档位列出 `I × PW` |
| 电荷密度 | 按每个触点真实面积计算，分段触点单独列 |
| Shannon `k` | 对最大电流、最大脉宽、最小触点面积计算 |
| 电压瞬态 | 测试阴极/阳极峰值是否越过材料安全水窗 |
| 残余 DC | 验证 charge-balanced，避免净直流 |
| 温升 | 高频/高占空比刺激下评估 |
| 脉冲后 EIS/CV | 长时间刺激后确认阻抗和 CSC/CIC 无异常劣化 |

## 7. 刺激伪迹和采集前端（加强）

### 7.1 DBS 采集的核心困难

OFF-stim 状态采到 LFP 只是第一步。闭环 DBS 更难的是 ON-stim 状态下估计 biomarker。LFP 目标频段常在 `1-500 Hz`，PD beta 常约 `13-30 Hz`；而 DBS 刺激常使用几十到一百多 Hz 的脉冲序列，刺激基频及谐波可能污染 LFP 频谱。<sup>[1][3][6][7]</sup>

### 7.2 伪迹来源和量化指标

| 伪迹来源 | 影响 | 建议量化 |
|---|---|---|
| 前端饱和 | 刺激脉冲瞬态过大，放大器恢复慢 | 饱和持续时间、恢复到基线所需时间 |
| 电极极化 | 刺激后慢漂移，污染低频 LFP | 刺激后 `10 ms/100 ms/1 s` 基线偏移 |
| 导线耦合 | 刺激通道串扰到记录通道 | 不同触点组合下伪迹幅度 |
| 频谱泄漏 | 刺激基频/谐波污染 beta/gamma | ON-stim PSD 与 OFF-stim PSD 差异 |
| blanking | 丢失刺激脉冲附近数据 | blanking 占空比、插值误差、对 beta power 的影响 |

Wu 等 2024 年闭环 DBS AFE 设计把 stimulation artifact tolerance 作为核心指标，说明伪迹耐受已经是 DBS 采集系统的前端硬指标，而不是后处理附属问题。<sup>[7]</sup>

### 7.3 建议的前端指标

以下为工程设计目标，不是统一法规阈值：

| 指标 | 建议目标 | 说明 |
|---|---|---|
| 输入参考噪声 | 低于目标 LFP 特征幅值一个数量级 | 若 beta 特征只有数 µV，前端噪声应尽量做到亚 µV 到低 µV rms |
| 输入动态范围 | 能承受刺激瞬态不长时间饱和 | ON-stim 采集必需 |
| 恢复时间 | 越短越好；闭环功率估计通常希望不影响 `100 ms-1 s` 特征窗口 | 需结合 blanking 策略 |
| CMRR | 高共模抑制 | 植入导线和 IPG 形成复杂共模路径 |
| 同步能力 | 刺激时钟与采样同步 | 有利于伪迹建模、blanking 和模板减除 |
| 输入保护 | 防止刺激脉冲损伤 AFE | 同一引线刺激/采集尤其重要 |

### 7.4 ON-stim 采集验证矩阵

| 条件 | 测什么 | 通过口径 |
|---|---|---|
| OFF-stim 基线 | 噪声、PSD、目标 biomarker | 建立参考基线 |
| 低幅刺激 ON-stim | 伪迹幅度、PSD 偏移 | 不破坏目标频段判读 |
| 最大临床刺激 ON-stim | 饱和恢复、电极极化、温升 | 不长时间饱和，恢复时间可接受 |
| 不同频率 | `60/90/130/180 Hz` 等 | 识别刺激基频/谐波对 LFP 频谱影响 |
| 不同触点组合 | 相邻双极、跨触点、单极 | 选择伪迹最小且 biomarker 稳定的组合 |
| 长时记录 | 小时级/天级漂移 | 验证慢性可用性 |

### 7.5 数据报告建议

DBS 采集论文或产品验证中，建议同时报告：

- OFF-stim 和 ON-stim 的 LFP PSD。
- 刺激参数：电流/电压、脉宽、频率、触点组合。
- 每个触点治疗阻抗和 EIS 阻抗。
- 伪迹峰值、饱和时间、恢复时间。
- blanking 窗口长度和占空比。
- 刺激伪迹处理前后的 beta/gamma biomarker 变化。
- 长期记录中 biomarker 可用率和通道失效率。<sup>[5][6][7]</sup>

## 8. 推荐测试方案

### 8.1 台架和体外电化学测试

| 测试 | 建议 | 主要依据 |
|---|---|---|
| EIS | PBS 或人工脑脊液，`37°C`，`1 Hz-100 kHz`，报告幅值和相位；至少报告 `1 kHz`。 | EIS 是植入电极界面表征的基础方法。<sup>[10][14][16]</sup> |
| CV/CSC | 明确参比电极、电位窗口、扫描速率、电解质、几何面积/有效面积。 | CSC 对方法高度敏感，必须带条件。<sup>[10]</sup> |
| CIC/电压瞬态 | 用接近 DBS 的脉宽、频率、电流范围测量，确认不越过安全电位窗口。 | CIC 和电压瞬态更接近刺激安全。<sup>[13][14]</sup> |
| 脉冲耐久 | 长时间双相脉冲刺激后重复 EIS/CV，观察阻抗、CSC、表面形貌。 | 刺激会改变界面状态，慢性可靠性必须验证。<sup>[10][12]</sup> |
| 污染/老化 | 蛋白浸泡、人工 CSF 浸泡、加速老化后重复 EIS/CV。 | 蛋白污染会降低有效面积和 CSC/CIC。<sup>[11]</sup> |
| 机械/封装 | 弯折、拉伸、连接器疲劳、涂层附着、绝缘泄漏。 | 长期植入可靠性是 DBS 核心约束。<sup>[14]</sup> |

### 8.2 动物或临床采集验证

| 验证项 | 建议 | 主要依据 |
|---|---|---|
| 植入后阻抗 | 急性、术后数周、慢性期连续记录。 | DBS 阻抗会随时间和触点激活状态变化。<sup>[12]</sup> |
| LFP 频谱 | 关注 beta、gamma、震颤频段或目标 biomarker 的 SNR 和稳定性。 | LFP biomarker 是感知/闭环 DBS 的基础。<sup>[1][3][4][6]</sup> |
| 刺激开关 | 分别评估 OFF-stim、ON-stim、刺激后恢复时间。 | 闭环 DBS 需处理刺激伪迹。<sup>[6][7]</sup> |
| 触点组合 | 单极、双极、相邻触点、跨触点组合比较。 | 触点位置和组合影响 LFP 解释。<sup>[1][3]</sup> |
| 慢性漂移 | 每周/月跟踪 PSD、阻抗、可用通道率。 | 长期无线记录研究强调慢性数据稳定性。<sup>[6]</sup> |
| 安全 | 电荷密度、温升、组织损伤、材料腐蚀、MRI/CT 兼容性按系统要求验证。 | 刺激安全需综合波形、材料、面积和组织反应。<sup>[13][14][17]</sup> |

## 9. 建议指标区间和适用边界

以下是工程调研阶段参考，不是法规或厂家阈值：

| 指标 | 临床 DBS 宏触点/分段触点 | 微电极/微阵列 | 说明 |
|---|---:|---:|---|
| 治疗阻抗 | 常见数百到数千 Ω；约 `500-2000 Ω` 可作为工程常见区间。<sup>[12][15][19]</sup> | 通常不适用 | 按设备测试模式定义异常阈值 |
| `1 kHz` 记录阻抗 | 宏触点常为低阻抗，通常低 kΩ 或以下更有利。<sup>[10][14]</sup> | 可为几十 kΩ到 MΩ。<sup>[9][14]</sup> | 必须报告相位和测试条件 |
| LFP 频段 | 常看 `1-500 Hz`，PD beta 常约 `13-30 Hz`。<sup>[1][3][6]</sup> | 取决于研究目标 | 不同疾病 biomarker 不同 |
| 每相电荷密度 | 按触点面积、材料和厂家限制计算。<sup>[13][14]</sup> | 更敏感，必须单独计算 | 分段/微触点面积小，不能沿用宏触点经验 |
| 刺激后恢复 | 越短越利于闭环；需结合 blanking 和 AFE 设计。<sup>[7]</sup> | 同左 | 单纯电极指标不够，需要系统级测试 |
| CSC/CIC | 不设通用数值，必须带 CV/脉冲条件。<sup>[10][13][14]</sup> | 同左 | CIC/电压瞬态比孤立 CSC 更接近 DBS 安全 |

## 10. 英文缩写和基本概念对照表

| 缩写 | 英文全称 | 中文含义 | 基本概念 |
|---|---|---|---|
| AFE | analog front-end | 模拟前端 | 连接电极和 ADC/数字处理的低噪声放大、滤波、保护电路 |
| aDBS | adaptive deep brain stimulation | 自适应 DBS | 根据 LFP 或症状相关特征动态调整刺激参数 |
| ADC | analog-to-digital converter | 模数转换器 | 将模拟 LFP 信号转换为数字数据 |
| BCI | brain-computer interface | 脑机接口 | 用神经信号驱动外部设备或调控系统 |
| CIC | charge injection capacity | 电荷注入能力 | 在安全电位窗口内每单位面积可注入的电荷能力 |
| CPE | constant phase element | 常相位元件 | EIS 中描述非理想电容/粗糙界面的等效元件 |
| CSC | charge storage capacity | 电荷存储能力 | CV 测得的电极可存储/释放电荷能力 |
| CSF | cerebrospinal fluid | 脑脊液 | DBS 电极周围可能接触的体液环境 |
| CV | cyclic voltammetry | 循环伏安 | 扫描电位并测电流，用于分析电化学反应和 CSC |
| DBS | deep brain stimulation | 深部脑刺激 | 植入电极向深部脑区施加电脉冲的治疗技术 |
| DC | direct current | 直流 | 净直流可能导致不可逆电化学反应，应避免 |
| EEG | electroencephalography | 脑电图/脑电采集 | 头皮或颅内神经电信号采集的统称；本文重点不是头皮 EEG |
| EIS | electrochemical impedance spectroscopy | 电化学阻抗谱 | 频率扫描阻抗，表征电极-组织界面 |
| EO | ethylene oxide | 环氧乙烷 | 常见医疗器械灭菌方式 |
| GPi | globus pallidus internus | 苍白球内侧部 | 常见 DBS 靶点 |
| IPG | implantable pulse generator | 植入式脉冲发生器 | DBS 系统中产生刺激脉冲的植入设备 |
| IrOx | iridium oxide | 氧化铱 | 高电容/高电荷注入能力电极材料 |
| LFP | local field potential | 局部场电位 | 植入电极记录的局部群体神经电活动 |
| MER | microelectrode recording | 微电极记录 | DBS 手术或研究中用微电极记录单位放电/局部活动 |
| MRI | magnetic resonance imaging | 磁共振成像 | DBS 系统需考虑 MRI 安全/兼容性 |
| NAc | nucleus accumbens | 伏隔核 | 精神/奖赏相关 DBS 靶点之一 |
| OFF-stim | stimulation off | 刺激关闭状态 | 无 DBS 脉冲时的记录状态 |
| ON-stim | stimulation on | 刺激开启状态 | DBS 脉冲存在时的记录状态 |
| PBS | phosphate-buffered saline | 磷酸盐缓冲液 | 常用体外电化学测试溶液 |
| PD | Parkinson's disease | 帕金森病 | DBS 常见适应证之一 |
| PEDOT | poly(3,4-ethylenedioxythiophene) | 聚 3,4-乙烯二氧噻吩 | 常见导电聚合物涂层 |
| PSD | power spectral density | 功率谱密度 | 分析 LFP 各频段能量的常用指标 |
| PtIr | platinum-iridium | 铂铱合金 | 临床 DBS 常见触点材料 |
| PW | pulse width | 脉宽 | 单相刺激持续时间，决定每相电荷 |
| SEM | scanning electron microscopy | 扫描电子显微镜 | 观察电极表面形貌和涂层状态 |
| SNR | signal-to-noise ratio | 信噪比 | 目标神经信号相对噪声的强弱 |
| STN | subthalamic nucleus | 丘脑底核 | 帕金森病 DBS 常见靶点 |
| TiN | titanium nitride | 氮化钛 | 常见低阻抗高表面积电极涂层 |
| VIM | ventral intermediate nucleus | 丘脑腹中间核 | 震颤相关 DBS 靶点 |

## 11. 可用于 PPT 的参考图建议

下表只列文献 `9-15` 和 `17` 中可能值得用于 PPT 说明的图类，并标明当前核查状态。需要特别说明：文献 9 的 ACS 页面未能下载全文，因此不能确认具体正文图号；下表对文献 9 的内容只作为“打开全文后优先查找的图线索”，不能当作已经核过原图。

若是组内汇报，通常可以在图下标明“来源：文献[n]”作为学术引用；若用于公开报告、论文、商业材料或专利附件，优先复绘或走出版社授权。最稳妥的做法是：实物/显微图可引用原图，公式模型、EIS/CV、Shannon 安全边界尽量按原文数据或公式复绘。

| 文献 | 当前核查状态 | 可查找/可复绘的图类 | 适合说明的问题 | 使用建议 |
|---|---|---|---|---|
| [9](https://doi.org/10.1021/acssensors.3c02676) | PubMed 题录可核；未下载全文 | 打开全文后优先查找微电极阵列结构图、深部脑区植入/刺激示意图、EIS 或阻抗性能图 | 可作为微电极/微阵列与 DBS 宏触点尺度差异的补充材料 | 不能直接声称已核正文图；需拿到 PDF 后再确认具体图号和图注 |
| [10](https://doi.org/10.1088/1741-2552/abd897) | IOP 页面和 PubMed 摘要可核；未成功抓取 PDF/XML 图注 | CV 曲线、CSC 计算相关图、EIS/Bode 图、有效电极面积比较图 | 摘要明确涉及 CV、EIS、有效电极面积、CSC 依赖测量方法和电极结构 | 最适合支撑第 6.1 节 CSC 概念；图号需拿到 PDF 后确认 |
| [11](https://doi.org/10.1002/celc.202001574) | 仅核到 Crossref/DOI 题录和出版社入口；未下载全文 | 蛋白污染前后 EIS、CIC、有效电极面积变化图 | 题名和 DOI 元数据支持其主题，但具体图号未核 | 拿到 PDF 后再确认图号；公开使用 Wiley 图通常需授权 |
| [12](https://doi.org/10.1159/000358014) | PubMed 摘要和 PMC 全文可核；已核到图注 | 阻抗随植入时间变化图；各触点阻抗斜率分布图 | 摘要可核 `84` 名患者、`128` 根电极、`73 Ω/year`、`72%`、`163 Ω` 等数据 | 可优先复绘 PMC 图 1/图 2 的趋势；直接贴图前仍需确认授权 |
| [13](https://doi.org/10.1016/j.jneumeth.2004.10.020) | PubMed 摘要可核；出版社全文访问受限 | 安全刺激波形、电荷平衡、电极电位/电压瞬态、电荷密度概念图 | 摘要明确涉及电极-组织界面、Faradaic/non-Faradaic、电极电位、刺激安全 | Elsevier 图直接粘贴通常有版权限制；建议按概念复绘 |
| [14](https://doi.org/10.1146/annurev.bioeng.10.061807.160518) | PubMed 摘要可核；出版社全文访问受限 | 神经电极界面模型、材料/涂层对 CSC/CIC 和阻抗的影响、记录/刺激电极对比图 | 摘要明确涉及 TiN、Pt、IrOx、charge-balanced waveforms 和电化学表征 | Annual Reviews 图通常版权较严；更适合作为复绘依据 |
| [15](https://doi.org/10.1093/ons/opz035) | PubMed 摘要可核；出版社全文访问受限 | 术中高阻抗案例图、影像/触点位置图、阻抗异常处理流程相关图 | 摘要可核其为 DBS 术中高阻抗与 pneumocephalus 相关病例 | 适合做临床异常案例页；具体图号需拿到 PDF 后确认 |
| [17](https://doi.org/10.1109/10.126616) | PubMed 题录、DOI 和 IEEE 入口可核；未下载全文 | Shannon 安全模型图：每相电荷 `Q` 与电荷密度 `D` 的安全边界 | 作为经典安全模型引用；正文图建议按公式复绘而不是直接粘贴 | 不建议直接贴 IEEE 原图；建议用文中公式 `k = log10(D) + log10(Q)` 自己画安全边界图 |

PPT 里最建议使用的 4 张图是：

1. 文献 12 的 DBS 阻抗长期变化图：PMC 全文可核，适合说明慢性阻抗不是固定值，而会随时间和触点激活状态变化。
2. 文献 10 的 CV/EIS/CSC 图：PubMed 摘要可核主题，适合说明 CSC 的测量来源和为什么要带测试条件；具体图号需 PDF 确认。
3. 文献 11 的蛋白污染前后对比图：目前仅作为查图线索，需 PDF 确认图号；适合说明表面污染会改变阻抗、CIC 和有效面积。
4. 文献 17 的 Shannon 安全边界复绘图：说明电荷密度和每相电荷共同决定刺激安全余量。

### 11.1 新增可下载文献的图建议

下表只针对新增的可下载/开放全文文献 `[20]-[26]`，用于加强上文四张表的图示说明。优先级按 PPT 解释价值排序；若篇幅有限，优先选“建议必加”的图。

| 对应表格 | 建议图 | 是否建议加入 | 可说明的问题 |
|---|---|---|---|
| 电极形态与阻抗量级 | 文献 `[25]` Fig. 1：常规 DBS 电极、8 触点 directional lead、40 触点 lead 设计示意 | 建议必加 | 直接解释为什么有环形触点、分段触点、多触点/高密度 DBS lead；适合放在“电极形态”表旁边。 |
| 电极形态与阻抗量级 | 文献 `[25]` Fig. 2：directional DBS 的 current steering 概念图 | 建议加入 | 说明分段触点不是单纯“更多触点”，而是为了把电流导向 therapeutic sweet spot、避开 side-effect sour spot。 |
| 电极形态与阻抗量级 | 文献 `[26]` Fig. 2：PEDOT:PSS ultramicroelectrode 的 EIS/1 kHz 阻抗随沉积变化 | 建议必加 | 说明微电极为什么常是高阻抗、涂层为什么能降阻抗；也能支撑“涂层/改性电极”行。 |
| 4.4 阻抗和热噪声量级估算 | 文献 `[20]` Fig. 3：DBS 电极体外/体内 impedance magnitude、phase、Nyquist plots | 建议必加 | 给出真实 DBS 电极 EIS 谱，支撑“阻抗不是单点数值，应报告频谱和相位”。 |
| 4.4 阻抗和热噪声量级估算 | 文献 `[21]` Fig. 2：植入 DBS 电极 EIS 测量配置和典型阻抗谱 | 建议加入 | 说明体内 DBS 阻抗既包含电极-电解质界面，也包含周围组织成分；适合解释 EIS 与治疗阻抗不同。 |
| 5.2 主要界面因素及量化指标 | 文献 `[22]` Fig. 6：蛋白吸附量与电极阻抗指标的关系 | 建议必加 | 直接支撑“蛋白吸附会改变阻抗/界面状态”，比只用文字解释更直观。 |
| 5.2 主要界面因素及量化指标 | 文献 `[22]` Fig. 12：cell cover 改变电极阻抗路径的示意图 | 建议必加 | 适合解释胶质/细胞覆盖后，电荷传输路径变复杂，导致阻抗、极化和记录稳定性变化。 |
| 5.2 主要界面因素及量化指标 | 文献 `[24]` Fig. 1：Foreign Body Reaction 的发生、进展和结局 | 建议必加 | 用一张图解释蛋白吸附、免疫细胞、胶质/纤维化包裹为什么是慢性植入电极的核心问题。 |
| 5.2 主要界面因素及量化指标 | 文献 `[24]` Fig. 2：降低异物反应的涂层/材料/药物释放策略 | 可选 | 适合放在“涂层脱落/表面改性”后面，说明为什么要做表面工程。 |
| 6.1 Q、D、CSC、CIC 概念表 | 文献 `[23]` Fig. 1：Pt 电极循环伏安曲线 | 建议必加 | 解释 CSC 来自 CV 曲线积分，不是孤立材料常数。 |
| 6.1 Q、D、CSC、CIC 概念表 | 文献 `[23]` Fig. 2：Pt 电极 cathodic/anodic chronopotentiometric curves | 建议必加 | 解释 CIC/电压瞬态为什么比 CSC 更接近刺激安全；能直观看出脉冲注入时电极电位如何变化。 |
| 6.1 Q、D、CSC、CIC 概念表 | 文献 `[20]` Fig. 6 或 Fig. 9：DBS 电极双相电流脉冲下的 voltage responses | 建议加入 | 把“每相电荷、脉宽、电压瞬态、极化恢复”连起来，适合和 `Q = I × PW` 的表一起讲。 |

如果 PPT 只能加 6 张图，建议选：

1. `[25]` Fig. 1：DBS 电极形态总览。
2. `[20]` Fig. 3：DBS 电极体内/体外 EIS 谱。
3. `[22]` Fig. 6：蛋白吸附与阻抗变化。
4. `[24]` Fig. 1：异物反应/胶质包裹过程。
5. `[23]` Fig. 1：CV 曲线解释 CSC。
6. `[23]` Fig. 2：chronopotentiometry 解释 CIC/电压瞬态。

## 12. 参考文献

1. Vaou O. E., Spidi M. D., Raike R., et al. Symptom optimization through sensing local field potentials: Balancing beta and gamma in Parkinson's disease. Deep Brain Stimulation, 2023. DOI: 10.1016/j.jdbs.2023.01.001.
2. Ledingham D., Baker M., Pavese N. Local field potentials: Therapeutic implications for DBS in dystonia including adaptive DBS for dystonia. Deep Brain Stimulation, 2024. DOI: 10.1016/j.jdbs.2024.03.003.
3. Asher E. E., Slovik M., Mitelman R., et al. Local field potential journey into the Basal Ganglia. Deep Brain Stimulation, 2024. DOI: 10.1016/j.jdbs.2024.03.002.
4. Mishra A., Shah H. A., McBriar J. D., Zamor C., Mammis A. Local Field Potentials in Deep Brain Stimulation: Investigation of the Most Cited Articles. World Neurosurgery: X, 2023. DOI: 10.1016/j.wnsx.2022.100140.
5. Swann N. C., de Hemptinne C., Miocinovic S., et al. Chronic multisite brain recordings from a totally implantable bidirectional neural interface: experience in 5 patients with Parkinson's disease. Journal of Neurosurgery, 2018. DOI: 10.3171/2016.11.JNS161162.
6. Gilron R., Little S., Perrone R., et al. Long-term wireless streaming of neural recordings for circuit discovery and adaptive stimulation in individuals with Parkinson's disease. Nature Biotechnology, 2021. DOI: 10.1038/s41587-021-00897-5.
7. Wu C. Y., Huang C. W., Chen Y. W., et al. Design of CMOS Analog Front-End Local-Field Potential Chopper Amplifier With Stimulation Artifact Tolerance for Real-Time Closed-Loop Deep Brain Stimulation SoC Applications. IEEE Transactions on Biomedical Circuits and Systems, 2024. DOI: 10.1109/TBCAS.2024.3352414.
8. Fleming J. E., Orlowski J., Lowery M. M., Chaillet A. Self-Tuning Deep Brain Stimulation Controller for Suppression of Beta Oscillations: Analytical Derivation and Numerical Validation. Frontiers in Neuroscience, 2020. DOI: 10.3389/fnins.2020.00639.
9. Jia Q., Duan Y., Liu Y., et al. High-Performance Bidirectional Microelectrode Array for Assessing Sevoflurane Anesthesia Effects and In Situ Electrical Stimulation in Deep Brain Regions. ACS Sensors, 2024. [DOI: 10.1021/acssensors.3c02676](https://doi.org/10.1021/acssensors.3c02676). [PubMed: PMID 38779969](https://pubmed.ncbi.nlm.nih.gov/38779969/).
10. Harris A. R., et al. Understanding charge transfer on the clinically used conical Utah electrode array: charge storage capacity, electrochemical impedance spectroscopy and effective electrode area. Journal of Neural Engineering, 2021. [DOI: 10.1088/1741-2552/abd897](https://doi.org/10.1088/1741-2552/abd897). [PubMed: PMID 33401255](https://pubmed.ncbi.nlm.nih.gov/33401255/).
11. Harris A. R., Carter P., Cowan R., Wallace G. G. Impact of Protein Fouling on the Charge Injection Capacity, Impedance, and Effective Electrode Area of Platinum Electrodes for Bionic Devices. ChemElectroChem, 2021. [DOI: 10.1002/celc.202001574](https://doi.org/10.1002/celc.202001574).
12. Satzer D., Lanctin D., Eberly L. E., Abosch A. Variation in Deep Brain Stimulation Electrode Impedance over Years Following Electrode Implantation. Stereotactic and Functional Neurosurgery, 2014. [DOI: 10.1159/000358014](https://doi.org/10.1159/000358014). [PubMed: PMID 24503709](https://pubmed.ncbi.nlm.nih.gov/24503709/). [PMC: PMC4531050](https://pmc.ncbi.nlm.nih.gov/articles/PMC4531050/).
13. Merrill D. R., Bikson M., Jefferys J. G. R. Electrical stimulation of excitable tissue: design of efficacious and safe protocols. Journal of Neuroscience Methods, 2005. [DOI: 10.1016/j.jneumeth.2004.10.020](https://doi.org/10.1016/j.jneumeth.2004.10.020). [PubMed: PMID 15661300](https://pubmed.ncbi.nlm.nih.gov/15661300/).
14. Cogan S. F. Neural stimulation and recording electrodes. Annual Review of Biomedical Engineering, 2008. [DOI: 10.1146/annurev.bioeng.10.061807.160518](https://doi.org/10.1146/annurev.bioeng.10.061807.160518). [PubMed: PMID 18429704](https://pubmed.ncbi.nlm.nih.gov/18429704/). [PDF](https://microprobes.com/files/pdf/publications/gen-knowledge/cogan_2008_neural_stimulation.pdf).
15. Lyons M. K., Neal M. T., Patel N. P. Intraoperative High Impedance Levels During Placement of Deep Brain Stimulating Electrode. Operative Neurosurgery, 2019. [DOI: 10.1093/ons/opz035](https://doi.org/10.1093/ons/opz035). [PubMed: PMID 30860268](https://pubmed.ncbi.nlm.nih.gov/30860268/).
16. Manatchinapisit V., Constandinou T. G. A Portable and Low-cost Electrochemical Impedance Spectroscopy Platform for the Characterisation of Implantable Electrodes. EMBC, 2024. DOI: 10.1109/EMBC53108.2024.10782309.
17. Shannon R. V. A model of safe levels for electrical stimulation. IEEE Transactions on Biomedical Engineering, 1992. [DOI: 10.1109/10.126616](https://doi.org/10.1109/10.126616); [IEEE Xplore](https://ieeexplore.ieee.org/document/126616). [PubMed: PMID 1592409](https://pubmed.ncbi.nlm.nih.gov/1592409/).
18. Górecka J., Makiewicz P. The Dependence of Electrode Impedance on the Number of Performed EEG Examinations. Sensors, 2019. DOI: 10.3390/s19112608.
19. Butson C. R., Maks C. B., McIntyre C. C. Sources and effects of electrode impedance during deep brain stimulation. Clinical Neurophysiology, 2006. DOI: 10.1016/j.clinph.2005.10.007.
20. Wei X. F., Grill W. M. Impedance characteristics of deep brain stimulation electrodes in vitro and in vivo. Journal of Neural Engineering, 2009. [DOI: 10.1088/1741-2560/6/4/046008](https://doi.org/10.1088/1741-2560/6/4/046008). [PubMed: PMID 19587394](https://pubmed.ncbi.nlm.nih.gov/19587394/). [PMC: PMC3066196](https://pmc.ncbi.nlm.nih.gov/articles/PMC3066196/).
21. Lempka S. F., Miocinovic S., Johnson M. D., Vitek J. L., McIntyre C. C. In vivo impedance spectroscopy of deep brain stimulation electrodes. Journal of Neural Engineering, 2009. [DOI: 10.1088/1741-2560/6/4/046001](https://doi.org/10.1088/1741-2560/6/4/046001). [PubMed: PMID 19494421](https://pubmed.ncbi.nlm.nih.gov/19494421/). [PMC: PMC2861504](https://pmc.ncbi.nlm.nih.gov/articles/PMC2861504/).
22. Newbold C., Richardson R., Millard R., Huang C., Milojevic D., Shepherd R., Cowan R. Changes in biphasic electrode impedance with protein adsorption and cell growth. Journal of Neural Engineering, 2010. [DOI: 10.1088/1741-2560/7/5/056011](https://doi.org/10.1088/1741-2560/7/5/056011). [PubMed: PMID 20841637](https://pubmed.ncbi.nlm.nih.gov/20841637/). [PMC: PMC3543851](https://pmc.ncbi.nlm.nih.gov/articles/PMC3543851/).
23. Harris A. R., Newbold C., Carter P., Cowan R., Wallace G. G. Using Chronopotentiometry to Better Characterize the Charge Injection Mechanisms of Platinum Electrodes Used in Bionic Devices. Frontiers in Neuroscience, 2019. [DOI: 10.3389/fnins.2019.00380](https://doi.org/10.3389/fnins.2019.00380). [PubMed: PMID 31118879](https://pubmed.ncbi.nlm.nih.gov/31118879/). [PMC: PMC6508053](https://pmc.ncbi.nlm.nih.gov/articles/PMC6508053/). [PDF](https://www.frontiersin.org/journals/neuroscience/articles/10.3389/fnins.2019.00380/pdf).
24. Gori M., Vadalà G., Giannitelli S. M., Denaro V., Di Pino G. Biomedical and Tissue Engineering Strategies to Control Foreign Body Reaction to Invasive Neural Electrodes. Frontiers in Bioengineering and Biotechnology, 2021. [DOI: 10.3389/fbioe.2021.659033](https://doi.org/10.3389/fbioe.2021.659033). [PubMed: PMID 34113605](https://pubmed.ncbi.nlm.nih.gov/34113605/). [PMC: PMC8185207](https://pmc.ncbi.nlm.nih.gov/articles/PMC8185207/). [PDF](https://www.frontiersin.org/journals/bioengineering-and-biotechnology/articles/10.3389/fbioe.2021.659033/pdf).
25. Steigerwald F., Matthies C., Volkmann J. Directional Deep Brain Stimulation. Neurotherapeutics, 2019. [DOI: 10.1007/s13311-018-0667-7](https://doi.org/10.1007/s13311-018-0667-7). [PubMed: PMID 30232718](https://pubmed.ncbi.nlm.nih.gov/30232718/). [PMC: PMC6361058](https://pmc.ncbi.nlm.nih.gov/articles/PMC6361058/).
26. Jones P. D., Moskalyuk A., Barthold C., Gutöhrlein K., Heusel G., Schröppel B., Samba R., Giugliano M., et al. Low-Impedance 3D PEDOT:PSS Ultramicroelectrodes. Frontiers in Neuroscience, 2020. [DOI: 10.3389/fnins.2020.00405](https://doi.org/10.3389/fnins.2020.00405). [PubMed: PMID 32508562](https://pubmed.ncbi.nlm.nih.gov/32508562/). [PMC: PMC7248397](https://pmc.ncbi.nlm.nih.gov/articles/PMC7248397/). [PDF](https://www.frontiersin.org/journals/neuroscience/articles/10.3389/fnins.2020.00405/pdf).
