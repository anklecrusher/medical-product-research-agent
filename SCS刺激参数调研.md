# SCS 刺激参数调研：电压、电流、频率、脉宽、阻抗与通道

调研日期：2026-06-11  
范围：以植入式硬膜外脊髓刺激（spinal cord stimulation, SCS）用于慢性疼痛/痛性糖尿病周围神经病变（PDN/PDPN）为主；不把经皮脊髓刺激（tSCS）和脊髓损伤运动恢复用 eSCS 作为主体。

## 1. 快速结论

- 近年临床论文最常报告的是**频率、脉宽、电流或电压、导联/触点配置**；**阻抗**通常不在疗效论文主参数表里，而是在设备完整性、MRI 条件性、能耗或程控技术论文中报告。
- 现代 SCS 多为恒流或可程控输出，所以论文常报 **mA**，很少直接报 **V**。电压可用 `V = I × Z` 估算，但必须同时给出阻抗来源。
- 典型范围大致如下：传统 tonic SCS 约 **30-100 Hz、150-500 μs**；10 kHz SCS 常见 **10 kHz、30 μs、0.5-3.5 mA**；BurstDR 常见 **5 个脉冲/簇、簇内 500 Hz、簇重复 40 Hz、1000 μs**；ECAP 闭环多以 **约 30 Hz** 运行并按每个刺激脉冲调节输出；DTM SCS 常用低频（<200 Hz）与高频（200-1200 Hz）多信号复用。

## 2. 临床论文/研究中的参数

NR = not reported（原文未直接报道）。

| 波形/应用 | 研究或资料 | 频率 | 脉宽 | 电流/电压 | 阻抗 | 通道/导联/触点 | 备注与来源 |
|---|---:|---:|---:|---:|---:|---:|---|
| 10 kHz SCS；PDN | Petersen et al., SENZA-PDN RCT, JAMA Neurology 2021 | 10 kHz | 30 μs | 0.5-3.5 mA | NR | 经皮导联；T8-T11 置入；临床资料常按双导联/双极输出描述 | 2025 综述表直接列出“10 kHz、30 μs、bipole、0.5-3.5 mA”：<https://www.mdpi.com/2227-9059/13/12/3063>；JAMA 原文：<https://jamanetwork.com/journals/jamaneurology/fullarticle/2777806>；PDF：<https://www.nevro.com/app/uploads/sites/2/2025/01/jamaneurology_petersen_2021_oi_210012_1622672611.82747.pdf> |
| 传统 tonic SCS；PDPN/DRG-S 对照 | Han & Cong, Frontiers in Neurology 2024 | 40-60 Hz | 180-240 μs | 0.5-2.0 V | NR | SCS 组：Medtronic SPECIFY 5-6-5 paddle lead，T10-T12；DRG-S 组：SPECIFY 2×8 双侧 L4-L5 | Device programming 段直接给出 40-60 Hz、180-240 μs、0.5-2.0 V：<https://www.frontiersin.org/journals/neurology/articles/10.3389/fneur.2024.1366796/full> |
| BurstDR / burst SCS | SUNBURST 及后续综述 | 簇内 500 Hz；簇重复 40 Hz | 1000 μs | 通常为低幅/亚感觉阈值；具体 mA 个体化 | NR | 多触点 SCS 系统；具体触点按患者程控 | Pain Medicine 综述给出“5 个 1000 μs 脉冲、500 Hz、40 Hz 重复”：<https://academic.oup.com/painmedicine/article/20/Supplement_1/S47/5509422>；SUNBURST DOI：<https://doi.org/10.1111/ner.12698>；低幅 burst 分析 PDF：<https://lab-clint.org/Published/2021_16.pdf> |
| DTM SCS | DTM SCS 综述/真实世界研究 | 低频 <200 Hz；高频 200-1200 Hz | 不同 base/prime 信号不同；具体算法为专有 | 按 6 个目标的 base/prime 振幅个体化 | NR | NICE 描述：3 个治疗选项，每个 4 个刺激信号；总计靶向 6 个解剖位置；常用 2 根经皮 Vectris leads | DTM 参数范围见 PMC 文章摘要/正文：<https://pmc.ncbi.nlm.nih.gov/articles/PMC11551985/>；NICE 技术说明：<https://www.nice.org.uk/advice/mib305/chapter/The-technology> |
| ECAP 阈值/感知阈值研究 | Pilitsis et al., Frontiers in Neuroscience 2021 | 50 Hz | 60、90、120 μs | 0 mA 起，0.1 mA 递增至感知阈值和不适阈值；研究系统最大 25 mA | NR | 商用 8 电极、60 cm 经皮 SCS 导联；两根部分重叠、交错置于 T9 附近；刺激为 guarded cathode/tripolar，记录在同/对侧导联端 | 原文 Materials and Methods 直接列出 60/90/120 μs、50 Hz、0.1 mA 步进、8 电极导联：<https://www.frontiersin.org/journals/neuroscience/articles/10.3389/fnins.2021.673998/full> |

## 3. 阻抗与电压：临床论文之外的关键数据

| 主题 | 数据 | 含义 | 来源 |
|---|---:|---|---|
| 典型经皮导联阻抗 | 颈段 351 ± 90 Ω；下胸段 547 ± 151 Ω | 下胸段阻抗约高 36%，提示胸段刺激在急性置入期能耗/电压需求可能更高 | Alo et al., Neuromodulation 2006，经 PubMed 摘要：<https://pubmed.ncbi.nlm.nih.gov/22151637/> |
| 高阻抗与 MRI 条件性 | 高阻抗可导致系统无法进入 MRI conditional mode；高阻抗可能来自导线断裂、导联移位、硬膜外纤维化、植入节段等 | 阻抗在临床上常被用作设备完整性/MRI 适配检查，而不是疗效参数 | Sayed et al., Pain and Therapy 2021：<https://link.springer.com/article/10.1007/s40122-020-00219-8> |
| 高阻抗阈值示例 | Boston Scientific Precision 手册中，>4500 Ω 的 contact 显示为 high impedance | 厂商阈值不同，不能把 4500 Ω 当所有 SCS 的通用阈值 | Precision SCS clinician manual PDF：<https://www.uhms.org/images/MEDFAQs/91083273-01_RevA_Precision_Spinal_Cord_Stimulator_System_Clinician_Manua.pdf> |
| 通道/输出能力示例 | Senza IPG 为 16 output channels | “通道”常对应 IPG 输出/触点可编程能力，和论文里的“导联数/触点数”不是同一个概念 | FDA Senza SCS SSED：<https://www.accessdata.fda.gov/cdrh_docs/pdf13/p130022b.pdf> |

## 4. 厂商/监管文件参数补充

厂商文件给出的多是**设备可编程/标称能力**，不等同于某个适应证的临床常用处方；实际可用组合还会被电荷密度、阻抗、频率-脉宽互锁、MRI 条件性和医生程控策略限制。

| 厂商/系统 | 文件类型 | 频率/Rate | 脉宽 | 电流/电压 | 阻抗/负载 | 通道/触点/程序 | 备注与来源 |
|---|---|---:|---:|---:|---:|---:|---|
| Medtronic Intellis LT | Medtronic SCS Product Performance Report | 40-1200 Hz | 60-1000 μs | 0-100 mA | NR | 最大 16 electrodes；1-3 groups；12 programs | FDA approval September 2017；属于较早的可充电 Intellis 平台型号，不是当前最新闭环款。PPR 页面：<https://www.medtronic.com/en-us/healthcare-professionals/product-resources/product-advisories-performance/neuromodulation-product-performance.html>；PDF：<https://www.medtronic.com/content/dam/medtronic-wide/public/united-states/products/neurological/product-performance-report-spinal-cord-stimulation-systems.pdf> |
| Medtronic Vanta with AdaptiveStim | Medtronic SCS Product Performance Report | 40-130 Hz | 60-450 μs | 0-100 mA | NR | 最大 16 electrodes；8 groups；32 programs | FDA approval June/July 2021；定位是 recharge-free/non-rechargeable（不可充电、长寿命）平台，不是 Intellis 的直接升级版。PPR：<https://www.medtronic.com/content/dam/medtronic-wide/public/united-states/products/neurological/product-performance-report-spinal-cord-stimulation-systems.pdf>；新闻稿：<https://news.medtronic.com/2021-06-10-Medtronic-Announces-FDA-Approval-of-its-Next-Generation-Recharge-Free-Spinal-Cord-Stimulation-Platform> |
| Medtronic Inceptiv | Medtronic SCS Product Performance Report | 2-1200 Hz | 60-1000 μs | 0-100 mA | NR | 最大 16 electrodes；8 groups；32 programs | FDA approval April 2024；当前较新的可充电闭环 SCS 平台，可感知 ECAP/神经反应并实时调节刺激。PPR：<https://www.medtronic.com/content/dam/medtronic-wide/public/united-states/products/neurological/product-performance-report-spinal-cord-stimulation-systems.pdf>；新闻稿：<https://news.medtronic.com/2024-04-26-Medtronic-receives-FDA-approval-for-Inceptiv-TM-closed-loop-spinal-cord-stimulator>；产品页：<https://www.medtronic.com/en-us/healthcare-professionals/products/neurological/spinal-cord-stimulation/neurostimulation-systems/inceptiv-neurostimulation-system.html> |
| Abbott Proclaim XR | FDA/Abbott clinician manual + device information | Tonic 2-1200 Hz 分段可调；BurstDR burst rate 10-60 Hz，intra-burst 250-1000 Hz | Tonic 20-1000 μs；Burst 50-1000 μs | Tonic 0-25.5 mA；Burst 0-12.75 mA | 最大电流受 impedance、frequency、pulse width 限制；电荷密度警告阈值 30 μC/cm² | up to 16 electrodes total；多个 stim sets 会影响 tonic 最大频率 | 表格用短名；完整常见写法是 Proclaim XR SCS System，Proclaim 是 Abbott 的 SCS 产品族。Proclaim XR clinician manual 说明 constant-current IPG、最多 16 electrodes、最大电流受阻抗/频率/脉宽限制：<https://manuals.eifu.abbott/content/dam/av/manuals-eifu/global/FI/en/ARTEN600080779_A.PDF>；Abbott 页面披露 30 μC/cm² charge-density warning：<https://www.neuromodulation.abbott/us/en/healthcare-professionals.html>；Proclaim Elite device information 给出参数范围表：<https://braininitiative.nih.gov/sites/default/files/documents/proclaim_elite_scs_device_information_508c.pdf> |
| Boston WaveWriter Alpha | Instructions for Use | 2-1200 Hz，默认 40 Hz | 20-1000 μs，默认 210 μs | 0-25.5 mA，默认 0 mA | IFU 要求连接前检查 impedances；电池估算使用 system/lead impedance | 最多 4 个刺激区域/通道；16 触点脉冲发生器可使用 1-16 个触点；32 触点脉冲发生器可使用 1-32 个触点；支持 8、16、32 触点导联 | 表格用短名；完整常见写法是 Boston Scientific WaveWriter Alpha SCS System / WaveWriter Alpha Prime SCS System。IFU 规格表：<https://www.bostonscientific.com/content/dam/elabeling/nm/92469342-02_WaveWriter_Alpha_and_WaveWriter_Alpha_Prime_Implantable_Pulse_Generator_multi-OUS_s.pdf>；患者信息说明电池受 amplitude/rate/pulse width/electrode number/stimulation areas/system impedance 影响：<https://www.bostonscientific.com/content/dam/elabeling/nm/97035847-02B_Info_Pts_Alpha_Prime_DPNVB_US_EN_s.pdf> |
| Nevro Senza / Senza II / Senza Omnia | Physician implant manual / Information for prescribers | 2-10,000 Hz；2-1200 Hz 为 paresthesia-based，10,000 Hz 为 paresthesia-free | 20 μs-1 ms | 0-15 mA | 最大 15 mA 输出时：400 Hz、1 ms 对应最大 1270 Ω；10,000 Hz、30 μs 对应最大 1080 Ω | IPG 16 output channels；Senza Omnia 可覆盖/组合 2-1200 Hz 与 10,000 Hz | Physician manual 规格表：<https://s28.q4cdn.com/260621474/files/doc_downloads/physician_manual/2021/07/Physician-Implant-Manual-%2811051%29.pdf>；HFX iQ prescriber manual 类似列 2-10,000 Hz、20-1000 μs、0-15 mA：<https://s28.q4cdn.com/260621474/files/doc_downloads/2022/12/16/10001223-Information-For-Prescribers-Rev-B_Final.pdf>；Omnia 产品页：<https://www.nevro.com/en/providers/product-omnia/> |
| Nevro HFX iQ / HFX Trial | Information for prescribers | 2-10,000 Hz | 20-1000 μs | 0-15 mA | HFX iQ 表：2 Hz 时 9 mA、1000 μs、1000 Ω；10,000 Hz 时 10 mA、30 μs、1000 Ω | NR | HFX iQ prescriber manual/FCC copy：<https://fcc.report/FCC-ID/XKYIPG3000/5885970.pdf>；Nevro 2025 reimbursement guide 说明 HFX iQ/Senza Omnia/HFX Trial 在 10 kHz 下的 PDN/NSBP 适应证：<https://www.nevro.com/app/uploads/2025/04/2025-Nevro-SCS-Reimbursement-Guide.pdf> |
| Saluda Evoke ECAP closed-loop | FDA clinical manual | Open-loop 10-1500 Hz；closed-loop 10-250 Hz | 20-1000 μs | 最大 stimulation current 1-50 mA；increment 0.05-4.0 mA | 手册有 impedance checks，但未在规格表给出常规阻抗范围 | 1 或 2 根导联，每根 12 electrodes；每个 program 最多 4 stimulation sets | 闭环时每个脉冲用 ECAP amplitude 调整下一脉冲电流；Clinical Manual：<https://www.accessdata.fda.gov/cdrh_docs/pdf19/P190002D.pdf>；Saluda manual portal：<https://manuals.saludamedical.com/hcp/saludamed/US/evoke?keycode=09352307000025> |
| Nalu Neurostimulation System | FDA 510(k) summary | 2-1500 Hz | 12-2000 μs，但会被 maximum phase charge/charge density 限制 | current-regulated；0-10.2 mA；在 300/500/800 Ω 下输出电压分别 0-3.1/5.1/8.2 V | 表格按 300、500、800 Ω 给出电压/电流/电荷密度；最大 phase charge 18.0 μC/pulse | 导联 distal end 为 4 或 8 cylindrical electrodes；RF transmit frequency 40.68 MHz | 510(k) summary 表 6.2：<https://www.accessdata.fda.gov/cdrh_docs/pdf20/K203547.pdf>；Nalu 患者 IFU：<https://nalumed.com/wp-content/uploads/2024/11/MA-000007-Nalu-Patient-Rev-N.pdf> |

### 厂商资料带来的几点补充判断

- **最大输出不是常用处方**：例如 Medtronic/Saluda/Nevro/Nalu 文件里可见几十 mA 或更宽的标称范围，但临床慢性疼痛处方通常低于设备最大输出，且会被舒适阈值和电荷安全限制约束。
- **美敦力三款不是同一代最新产品**：Intellis LT 是 2017 年左右的可充电平台型号；Vanta 是 2021 年的不可充电长寿命平台；Inceptiv 是 2024 年获 FDA 批准的可充电闭环平台，更接近当前旗舰/最新技术路线。
- **Inceptiv 的公开资料没有直接给出刺激电压上限**：Medtronic 官方公开规格只写到 `Amplitude 0-100 mA`、`Rate 2-1200 Hz`、`Pulse Width 60-1000 µsec`，没有单列最大刺激电压；如果要电压，只能再去看保密/完整植入手册或按阻抗做工程换算。
- **阻抗披露方式不同**：Nevro 与 Nalu 文件把阻抗直接放进输出能力表；Boston/Abbott/Medtronic 更多把 impedance 作为电池寿命、连接检查或 MRI/设备完整性条件。
- **“通道”口径不统一**：Boston 用 areas/channels 与 16/32 contacts；Nevro 写 16 output channels；Saluda 写 stimulation sets 与每根 12 electrodes；Medtronic PPR 写 maximum electrodes/groups/programs。
- **闭环系统要额外记录反馈参数**：Saluda Evoke 和 Medtronic Inceptiv 这类闭环系统，除频率/脉宽/电流外，还会涉及 ECAP/神经反应目标、检测算法和每脉冲调节逻辑。公开文件通常只披露高层能力，不披露完整控制算法。

## 5. 电压换算示例

这些是**推算值**，不是原文直接报道值；仅用于把 mA 与 V 放到同一量纲理解。

| 场景 | 已报道电流 | 阻抗假设 | 推算电压 |
|---|---:|---:|---:|
| 10 kHz SCS，SENZA-PDN | 0.5-3.5 mA | 下胸段典型 547 Ω | 约 0.27-1.91 V |
| 10 kHz SCS，SENZA-PDN | 0.5-3.5 mA | 颈段典型 351 Ω | 约 0.18-1.23 V |
| 传统 tonic，Han & Cong 2024 | 原文报道 0.5-2.0 V | 若按下胸段 547 Ω 反推 | 约 0.9-3.7 mA |

换算依据：`V = I × Z`，阻抗值来自 Alo et al. 2006，经 PubMed 摘要；10 kHz SCS 电流来自 SENZA-PDN 参数表；Han & Cong 2024 直接报告电压。

## 6. 对参数的工程/临床理解

- **频率**：传统 tonic 频率较低，常需产生 paresthesia；10 kHz、burst、DTM、部分闭环方案可做到亚感觉或无 paresthesia。
- **脉宽**：脉宽越宽，单位脉冲电荷越高；临床上会在覆盖范围、舒适性和能耗间折中。ECAP 阈值研究显示 60、90、120 μs 的感知阈值会随姿势和脉宽改变。
- **电流/电压**：恒流系统下，电压会随阻抗自动变化；恒压系统下，电流随阻抗变化。因此不同论文的 mA 和 V 不能直接横向比较。
- **阻抗**：更适合作为“导联-组织界面 + 设备回路状态”的指标。高阻抗提示可能的接触问题、导线断裂、导联移位、组织包裹或 MRI 条件性受限。
- **通道/触点**：临床论文常写“两根经皮导联”“8 触点导联”“paddle lead”等；设备文件则写 16 output channels、16 contacts 等。整理数据时应区分“IPG 输出通道”“导联触点数”“实际激活的阴极/阳极组合”。

## 7. 参考文献直达链接

1. Petersen et al. Effect of High-frequency (10-kHz) SCS in PDN, JAMA Neurology 2021：<https://jamanetwork.com/journals/jamaneurology/fullarticle/2777806>
2. Petersen et al. JAMA Neurology 2021 PDF mirror：<https://www.nevro.com/app/uploads/sites/2/2025/01/jamaneurology_petersen_2021_oi_210012_1622672611.82747.pdf>
3. Petersen et al. Long-term efficacy of 10 kHz SCS for PDN, Diabetes Research and Clinical Practice 2023 PDF：<https://www.nevro.com/app/uploads/2025/03/Petersen-2023-Long-term-efficacy-of-high-frequency-10-kHz-SCS-for-the-treatment-of-PDN.pdf>
4. Varrassi et al. Spinal Cord Stimulation in Painful Diabetic Neuropathy, Biomedicines 2025：<https://www.mdpi.com/2227-9059/13/12/3063>
5. Li et al. 10 kHz SCS vs traditional low-frequency SCS protocol, Frontiers in Neurology 2025：<https://www.frontiersin.org/journals/neurology/articles/10.3389/fneur.2025.1611970/full>
6. Han & Cong. SCS vs DRG-S in PDPN, Frontiers in Neurology 2024：<https://www.frontiersin.org/journals/neurology/articles/10.3389/fneur.2024.1366796/full>
7. Deer et al. SUNBURST study, Neuromodulation 2018：<https://doi.org/10.1111/ner.12698>
8. Burst SCS clinical review, Pain Medicine 2019：<https://academic.oup.com/painmedicine/article/20/Supplement_1/S47/5509422>
9. DTM SCS article, PMC：<https://pmc.ncbi.nlm.nih.gov/articles/PMC11551985/>
10. NICE DTM SCS technology briefing：<https://www.nice.org.uk/advice/mib305/chapter/The-technology>
11. Nijhuis et al. ECAP-controlled closed-loop SCS real-world, Pain and Therapy 2023：<https://link.springer.com/article/10.1007/s40122-023-00540-y>
12. Pilitsis et al. ECAP threshold and programming control, Frontiers in Neuroscience 2021：<https://www.frontiersin.org/journals/neuroscience/articles/10.3389/fnins.2021.673998/full>
13. Alo et al. Factors affecting impedance of percutaneous leads in SCS, PubMed：<https://pubmed.ncbi.nlm.nih.gov/22151637/>
14. Sayed et al. Failure of SCS MR-conditional modes due to high impedance, Pain and Therapy 2021：<https://link.springer.com/article/10.1007/s40122-020-00219-8>
15. FDA Senza SCS System SSED：<https://www.accessdata.fda.gov/cdrh_docs/pdf13/p130022b.pdf>
16. Boston Scientific Precision SCS clinician manual PDF：<https://www.uhms.org/images/MEDFAQs/91083273-01_RevA_Precision_Spinal_Cord_Stimulator_System_Clinician_Manua.pdf>
17. Medtronic SCS Product Performance Report：<https://www.medtronic.com/content/dam/medtronic-wide/public/united-states/products/neurological/product-performance-report-spinal-cord-stimulation-systems.pdf>
18. Medtronic Neuromodulation Product Performance page：<https://www.medtronic.com/en-us/healthcare-professionals/product-resources/product-advisories-performance/neuromodulation-product-performance.html>
19. Abbott Proclaim XR clinician manual：<https://manuals.eifu.abbott/content/dam/av/manuals-eifu/global/FI/en/ARTEN600080779_A.PDF>
20. Abbott neuromodulation HCP page：<https://www.neuromodulation.abbott/us/en/healthcare-professionals.html>
21. Proclaim Elite SCS Device Information：<https://braininitiative.nih.gov/sites/default/files/documents/proclaim_elite_scs_device_information_508c.pdf>
22. Boston Scientific WaveWriter Alpha/Alpha Prime IFU：<https://www.bostonscientific.com/content/dam/elabeling/nm/92469342-02_WaveWriter_Alpha_and_WaveWriter_Alpha_Prime_Implantable_Pulse_Generator_multi-OUS_s.pdf>
23. Boston Scientific WaveWriter Alpha Prime patient information：<https://www.bostonscientific.com/content/dam/elabeling/nm/97035847-02B_Info_Pts_Alpha_Prime_DPNVB_US_EN_s.pdf>
24. Nevro Senza/Senza II/Senza Omnia physician implant manual：<https://s28.q4cdn.com/260621474/files/doc_downloads/physician_manual/2021/07/Physician-Implant-Manual-%2811051%29.pdf>
25. Nevro HFX iQ information for prescribers：<https://s28.q4cdn.com/260621474/files/doc_downloads/2022/12/16/10001223-Information-For-Prescribers-Rev-B_Final.pdf>
26. Saluda Evoke SCS clinical manual：<https://www.accessdata.fda.gov/cdrh_docs/pdf19/P190002D.pdf>
27. Nalu Neurostimulation System FDA 510(k) summary：<https://www.accessdata.fda.gov/cdrh_docs/pdf20/K203547.pdf>
