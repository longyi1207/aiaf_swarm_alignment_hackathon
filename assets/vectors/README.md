# 向量文件来源

全部来自 LY 2026 年 8 月的 ToM / 共情分离实验（公开仓库 `longyi1207/tom-empathy-dissociation`，MIT；原始工作目录 `ai_lab/code/tom_empathy/outputs/vectors/`）。模型：`Qwen/Qwen3.5-9B`（32 层，hidden 4096），Mistral 文件除外。

| 文件 | sha256 | 内容 |
|---|---|---|
| `axes_vectors.pt` | `ce239044e347834996ba890741e43865fff33d1b87e751bdd378b3623d4c6ece` | 粗方向（diff-of-means），每层一份：`tau`（ToM，best_layer=8）、`epsilon`（共情，best_layer=17）、`sigma`（SOO，early_layer_flag=True，不建议用）、`tau_orth`/`epsilon_orth`（互相正交化后，L8 / L17） |
| `axes_vectors_sae.pt` | `bc27ce6ee27a2c6731cac6a4e55cdb24b63b225d55701396d6b66c81a7e9a13b` | 上面全部 + SAE 解码方向：`sae_tau_top1`、`sae_tau_top10_f0..f9`（L8）、`sae_epsilon_top1`（L17）。SAE：Qwen-Scope `Qwen/SAE-Res-Qwen3.5-9B-Base-W64K-L0_100` |
| `axes_vectors_random.pt` | `a6d476744b97cbfdd1acf1cadc6b8708000bcb1098638693ad277faf0989eaa5` | 随机对照：`sae_random_top10_f0..f9`（L8）及多层随机特征 |
| `axes_vectors_sae_v2.pt` | `e4123b513dc3171decced3b45c0309ff74d32ba0ead47a0da8958e97216863e8` | **2026-11-03 新增**：在 `axes_vectors_sae.pt` 的基础上，加了 `sae_epsilon_top10_f0..f9`（L17，ε 探针排名前 10 的 SAE 特征：3023, 21677, 60941, 50081, 25243, 31249, 9797, 63995, 42886, 32710）和 `sae_random_L17_f0..f9`（L17 的 10 个随机 SAE 特征，种子 20261103，排除了探针前 15 名）。由 `scripts/build_sae_axes.py` 生成，已核对 f0 与 8 月的 `sae_epsilon_top1` 一致（cos = 1.000000） |
| `axes_vectors_mistral.pt` | `b95d77427cb6cf09faa2a38352cb66a0a56f10bd53d8f3b703d888edcb2067a3` | `mistralai/Mistral-7B-Instruct-v0.3` 的粗方向（跨模型复现用） |

`configs/lesions.yaml` 里记录了这些 sha256，加载时会校验。

## 8 月的结论（和本实验有关的部分）

摘自 `tom-empathy-dissociation/RESULTS.md`：

- τ 和 ε 能干净地提取，且几乎正交（|cos| 基本 < 0.2）。
- 粗方向的单层消融**几乎不改变**单 agent 的 ToM / 共情任务（RQ2 null，在两个模型上都复现）。
- **最扎实的结果**：重度 SAE 级 τ 消融（top-10 特征）让模型**分不清"我知道的"和"别人知道的"**。随机特征对照排除了"任意扰动"的解释。副作用是"任务框架崩坏"和一种新的安全拒答，本实验要单独测量。
- 共情目前只有 1 个主导 SAE 特征（`sae_epsilon_top1`）；方向本身只约 30% 对齐这个特征。

## 探针排名

`sae_probe_tau.json` 和 `sae_probe_epsilon.json` 来自 8 月的 `src/sae_probe.py`。做法是：把提取方向用的对比句送进 SAE，按两组之间的平均激活差 |mean_diff| 给 SAE 特征排序。τ 和 ε 的 top-10 都按这个排名选取。

两点说明：
- 排名里有负的 mean_diff，例如 ε 的第 5–8 名。这些特征在共情一侧**更不活跃**。消融是把这个方向整个投影掉，和符号无关，这一点和 8 月 τ 的做法一致。
- τ 的差异整体比 ε 小一个数量级（τ 的 mean_diff 约 0.1，ε 约 1.0）。所以"同样 10 个特征"不等于"同样强度"，这正是 Phase 0b 要实测配平的原因。
