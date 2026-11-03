# aiaf_swarm_alignment_hackathon

**削弱 AI agent 的读心能力（ToM）和共情，看一群 agent 在"举报还是沉默"的困境里会怎么做。**

AIAF × Apart **Swarm Alignment Hackathon**（2026-11-06 → 08），Track 2 "Science of agent networks"。作者：Long Yi。

> 本仓库在黑客松开始前建立；赛前完成的部分（设计、世界生成器、损伤模块）会在提交时申报为已有工作。

## 一句话

5 个 AI 审核 agent 审一款血糖仪的验证数据（真实的 Excel 和 Word 文件，要联表计算）。数据里有人造假，但只有部分 agent 看得到。规则要求举报，可是**至少 3 个一起举报才立案**；人数不够，举报者会被踢出项目，他们剩下的合同钱平分给留下的人。

我们在推理时削弱部分 agent 的 ToM 和/或共情，比较"可以商量"和"不可以商量"两种条件。

完整设计：**[docs/设计.md](docs/设计.md)**

## 现在的进度

| 部分 | 状态 |
|---|---|
| 实验设计 | v0.2 草稿，有待定项（见设计 §9） |
| 世界生成器（Excel、docx、规则、标准答案） | ✅ 完成，有测试 |
| 参考解答器（按 SOP 从文件算出答案） | ✅ 完成；每个世界都会校验"文件 ⇒ 标准答案" |
| 收益规则（POL-ESC-007） | ✅ 完成，有测试 |
| 损伤模块（按行开关、向量校验） | ✅ 完成，有测试（数学和 8 月一致） |
| agent harness（工具、讨论频道、PRED-1、提交） | ⏳ 下一步 |
| 批量运行器（Spark 上的断点续跑、日志） | ⏳ |
| 分析与图表 | ⏳ |

## 快速开始

```bash
uv sync --group dev
uv run pytest -q                                   # 世界与收益的测试（无需 GPU）
uv run --extra model --group dev pytest -q         # 加上损伤模块的测试（需要 torch）

# 生成一个世界：5 个 agent、门槛 3、3 个看到造假、高伤害、可以商量
uv run swarmtom gen-world --seed 1 --k-evidence 3 --harm high --communication discuss --out worlds
# 校验：只用 agent 能看到的文件，按 SOP 重新算一遍，必须和标准答案一致
uv run swarmtom check-world worlds/w0001_n5_t3_k3_high_discuss
```

`examples/` 里有两个已生成的世界，可以直接打开 Excel 和 Word 看逼真程度：
- `w0001`：3 人看到造假、高伤害、可以商量
- `w0002`：2 人看到造假、低伤害、不可以商量

## 目录

```
docs/设计.md                    实验设计（中文，主文档）
docs/archive/                  早期英文草稿
configs/lesions.yaml           损伤条件（哪些向量、哪一层），带 sha256 校验
assets/vectors/                ToM / 共情向量（来自 8 月实验，见其 README）
src/swarmtom/world/            世界生成：spec、名字、数据、文档、SOP 解答器、收益
src/swarmtom/lesion/           推理时损伤：hooks（按行开关）、条件加载
src/swarmtom/cli.py            命令行：gen-world / check-world
tests/                         测试
examples/                      示例世界（标准答案在 ground_truth.json，agent 看不到）
```

## 说明

- 所有公司、产品、人名都是虚构的。
- 场景文本是英文，因为向量是用英文提示提取的，黑客松也用英文；项目文档用中文。
- 损伤**不改模型权重**：推理时在指定层把方向从隐藏状态里减掉。所有 agent 共用一份权重。

MIT License。
