# 医疗产品调研报告模板 v0.1

本模板用于医疗产品调研 Agent 的 Markdown 报告生成。它不是固定大纲，而是“固定骨架 + 可插拔章节块 + 图文资产位”。

## 固定骨架

每份报告至少应包含：

1. 核心结论
2. 关键参数与证据
3. 工程/产品理解
4. 风险、边界与未确认项
5. 参考文献与来源链接

## 可插拔章节块

下列章节按调研主题和证据密度启用：

| block_id | 标题 | 是否必需 | 适用场景 |
|---|---|---:|---|
| core_conclusion | 核心结论 | 是 | 所有报告 |
| parameter_evidence | 关键参数与证据 | 是 | 参数、竞品、工程指标类调研 |
| clinical_evidence | 临床论文/研究证据 | 否 | 有论文或临床研究证据时 |
| competitor_comparison | 竞品/厂商对照 | 否 | 有多个产品或厂商资料时 |
| regulatory_summary | 监管/注册资料补充 | 否 | 有 FDA、NMPA、NICE、ClinicalTrials 等资料时 |
| concept_explanation | 基础概念与机制解释 | 否 | 题目涉及专业概念或工程机制时 |
| engineering_analysis | 工程换算与产品解释 | 否 | 需要电压/电流/阻抗/电荷密度等换算时 |
| test_plan | 推荐测试或验证方案 | 否 | 需要研发验证、台架测试或临床验证建议时 |
| risks_and_gaps | 风险、边界与未确认项 | 是 | 所有报告 |
| references | 参考文献与来源链接 | 是 | 所有报告 |

## 图文资产位

报告允许直接嵌入从论文、厂商资料、监管资料中筛选出的有价值原图。

每张图必须记录：

- `figure_id`
- `title`
- `caption`
- `image_path` 或 `image_url`
- `source_id`
- `source_url`
- `source_title`
- `location`：例如页码、图号、章节或网页位置
- `recommended_section`
- `usage_note`
- `rights_note`

图缺失时，报告应显示“未找到适合本节的来源图，建议后续人工补图”，而不是失败。

## 引用与图注要求

- 每个关键结论必须能追溯到 `source_id` 或 `evidence_id`。
- 每张嵌入图必须有图题、图注和来源链接。
- 厂商资料图不得被表述为临床结论。
- 单篇论文图不得被表述为行业共识。

