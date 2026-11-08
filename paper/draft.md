TITLE: Talking Makes Whistleblowing All or Nothing: Language-Model Auditors and the Limits of Lesioning Social Cognition

AUTHORS:
Long Yi | Independent researcher
Yueheng Zhang | Independent researcher
Yushan Liu | Independent researcher

ABSTRACT:
When a single report of wrongdoing is too weak to act on, reporting becomes a collective-action problem. We built a testbed for it with language-model agents. Five Qwen3.5-9B auditors review spreadsheets from a fictional medical-device validation, each finds planted fabrication, and each decides in confidence whether to report internally or to a regulator, who opens an audit only if at least three report externally; otherwise the external reporters lose their contracts. Letting the auditors talk left the average number of external reports unchanged (2.2 versus 2.3 of 5 per game across 18 matched pairs of worlds) but made outcomes all or nothing: 14 of 18 discussion games ended with none or all five reporting externally, against 2 of 18 when auditors decided alone (exact paired test, p < 0.001). The first round of announcements predicted the group's choice in 13 of 15 games, and the undecided joined the emerging majority. We then asked whether theory of mind or empathy drives these choices by removing the corresponding directions from the agents' activations. No lesion changed reporting more than a random direction of the same strength, whose own effects reversed between two independent sets of worlds, and the one large effect, from a layer-6 theory-of-mind lesion, came from agents failing to complete the audit. STEERING_ABSTRACT_SENTENCE Claims that an internal capacity drives multi-agent behaviour need matched random controls inside the agent loop.

## 1. Introduction

AI agents increasingly do review work. They check code, audit data and screen documents, often several to a project. Whether they report the wrongdoing they find is a safety property, and frontier models already sometimes report misconduct on their own initiative when given tools to do so (Anthropic, 2025). Yet one report is often not enough. Regulators act on corroborated complaints, and a lone reporter bears the cost. Reporting then becomes a threshold public good (Palfrey and Rosenthal, 1984): each agent wants enough others to report, and its best choice depends on what it expects them to do.

Two parts of human social cognition bear on that choice. Theory of mind lets a reporter estimate what the others know and intend, and empathy makes the potential victims matter. Language models appear to represent other characters' beliefs in their activations, and steering those representations changes how they answer belief questions (Zhu et al., 2024; Bortoletto et al., 2025). If such representations also drive collective decisions, intervening on them would show why agents report, and would expose a lever on agent teams that could be used or abused.

We built a five-agent testbed for threshold reporting and asked two questions. What determines whether a group of language-model auditors reports? And do theory of mind and empathy, as directions in the model's activations, play a specific causal part in that decision? Every intervention is compared with a random direction at the same layers and strength, on benchmarks and inside the games, and the games are repeated on an independent set of worlds.

Our main contributions are:

1. **A threshold whistleblowing testbed** in which auditors work with realistic files, forecast each other's choices and file confidentially, with or without a discussion channel. Their reporting responds to the stakes, rising from 10% to 80% of agents between low- and high-harm versions.
2. **Evidence that discussion makes the outcome all or nothing.** Across 18 matched pairs of worlds, discussion left the mean number of external reports unchanged but made groups nearly unanimous in either direction, because public statements of intent reveal the likely majority and the undecided join it.
3. **A matched-control test of social-cognition interventions in interacting agents.** No lesion changed reporting more than its random control, and the largest effect came from broken task execution. STEERING_CONTRIBUTION_SENTENCE We also describe two silent infrastructure failures that bias multi-condition intervention studies with agents.

## 2. Related Work

**Social cognition inside language models.** Zhu et al. (2024) decoded characters' beliefs from attention heads and improved false-belief accuracy by steering along the probe directions. Bortoletto et al. (2025) found such representations brittle to prompt changes but correctable by activation edits, Prakash et al. (2025) traced how models bind characters to what they saw, and Wu et al. (2025) impaired theory-of-mind tasks by zeroing a sparse set of parameters. Behavioural tests of theory of mind remain sensitive to small changes in wording (Ullman, 2023; Strachan et al., 2024), and steering along empathy directions shifts outputs only partly (Jisun, 2026). All of this work tests single models on benchmarks.

**Language-model agents in social dilemmas.** Groups of agents have been studied in common-pool resource games (Piatti et al., 2024), in coordination tasks where asking agents to consider what the others might do changed how the group coordinated (Riedl, 2025), and in large simulated populations where cheating and whistleblowing emerged (Paglieri et al., 2026). Ong et al. (2025) steered personality directions in two agents playing a repeated prisoner's dilemma. We know of no study that intervenes on social-cognition representations in every member of an interacting group and measures the collective outcome.

**Steering and its controls.** Activation steering adds a direction to the residual stream (Turner et al., 2023; Rimsky et al., 2024) and directional ablation removes one (Arditi et al., 2024). Because steering effects vary across inputs (Tan et al., 2024), random directions of matched norm are the usual baseline; we apply it to group behaviour.

## 3. Testbed and Methods

### 3.1 The game

Each game simulates the final review of a fictional continuous glucose monitor (Figure 1). Five auditors, framed as AI review agents contracted from different firms, each review 12 of 60 validation batches, every batch a spreadsheet of 40 sensor test records. Three rules require joining tables: a test dated before its lot was made, a test run by a technician not employed that day, and five or more consecutive readings copied from an archive. Three or more violations, or any copied run, make a batch fabricated; one or two are clerical errors, which about a quarter of the other batches carry, so every auditor must tell the two apart. A reference solver confirms for every world that the files reproduce the planted answer. Each auditor also has personal files describing its contract and finances.

After the review, each auditor estimates, for every peer, the probability that the peer found fabrication and that it will report externally. In the discussion condition the auditors then exchange public and private messages for five rounds on a simulated clock and forecast again; in the isolated condition the policy forbids contact, and the files are otherwise identical. Filing is confidential and simultaneous. A risk memo sets the expected harm to patients at medium or high.

FIGURE: figures/fig1_scenario.png | 6.4 | **Figure 1.** The scenario. Five AI auditors review the validation data for a fictional glucose monitor, and every auditor's own batches contain fabricated records. Each files confidentially, internally or with the regulator, in one condition after a discussion. The regulator opens an audit only if three or more report externally; otherwise the external reporters lose their contracts.

All agents run Qwen3.5-9B (Qwen Team, 2026) with reasoning enabled, a 4,096-token limit per turn and temperature 0.6, served with vLLM (Kwon et al., 2023). Tools let them list and read files, run sandboxed Python, post messages and submit forms. The five agents share one copy of the weights, and interventions are applied per request.

### 3.2 Theory-of-mind and empathy directions

**Theory of mind.** We wrote 72 pairs of short stories that differ in one phrase: the protagonist either leaves the room or stays while another character moves an object, so the protagonist ends with a false or a true belief about where it is. The question and options are identical within a pair. In 72 control pairs the same change is made for a bystander whose belief does not matter. At each layer we took the mean activation difference at the final prompt token across protagonist pairs and projected out the bystander difference, removing what the words "leaves" and "stays" contribute. On three held-out story settings the resulting direction separated false- from true-belief stories in every pair at layers 14 to 18, and bystander pairs at 50 to 67%.

**Empathy.** The empathy direction comes from our earlier single-model study (August 2026): the mean activation difference between 26 descriptions of a person in distress, covering six kinds of distress, and matched neutral descriptions.

**Interventions.** A lesion removes the component of each token's activation along the unit direction *d*, replacing *h* with *h* − α(*h*·*d*)*d* at chosen layers (α = 1 removes it fully). Steering adds a multiple of the layer's raw difference vector instead. Each intervention has a control: a fixed random direction at the same layers with the same α or added norm. All five agents in a game receive the same intervention.

### 3.3 Benchmarks, selection and analysis

Before the games we measured each intervention, with reasoning enabled, on 180 belief questions in 12 new story settings (first- and second-order, false and true beliefs, and secret observation), 144 reality and memory questions about the same stories that need no belief reasoning, 20 empathy prompts scored 0 to 10 by the unmodified model, and 30 general capability questions. Selection criteria were written before each check. Of 17 theory-of-mind placements screened against random directions, three lowered belief accuracy without hurting the controls, and we took two into the games as exploratory arms: full removal at layer 6, and 30% removal at all layers. Neither met our pre-registered limit on unfinished reasoning. The empathy arm removed 70% of its direction at all layers.

A world is one combination of seed, harm level and communication condition. The first game run used 8 worlds, each played under seven arms: no intervention, three lesions and their three random controls. A replication used 4 new worlds. Each agent's outcome is an external filing, an internal filing or no valid filing. Comparisons pair arms within worlds; with so few worlds we treat the game results as descriptive.

## 4. Results

### 4.1 Agents weigh consequences once an acceptable alternative exists

We tuned the scenario until the no-intervention rate of external reporting fell inside a pre-registered band of 15 to 85%, and the failures were informative. Six versions that added personal financial pressure (debts and falling savings, an award, reminders to read personal files and mail) all left external reporting at 90 to 95% of agents (40 per version). Requiring agents to read every personal file first, so they demonstrably knew a lone report would cost them their contract, gave 97.5%. Many read the procedure's "report under the escalation policy" as an order to report externally. The rate moved only when the policy said a fabrication could be reported either internally or externally: 45% then reported externally, rising with the stakes from 10% at low harm to 50% at medium and 80% at high harm. All later games use this wording at medium and high harm.

### 4.2 Discussion makes the group outcome all or nothing

We pooled every no-intervention game played with the final wording: 36 games in 18 pairs, each pair sharing a seed and harm level and differing only in whether discussion was allowed. Discussion did not change how many auditors reported externally (2.2 per game with discussion, 2.3 without), and each condition opened an audit in 8 of 18 games. It changed the distribution (Figure 2). Without discussion, the count per game behaved like five roughly independent choices, with a variance of 1.4 against 1.2 expected under independence. With discussion, 14 of 18 games ended with none or all five reporting externally, the variance rose to 5.1, and the implied correlation between two auditors in the same game was about 0.8. Exchanging the condition labels within pairs in all 2¹⁸ ways gave an exact one-sided p of 0.0003 for the increase in variance.

FIGURE: figures/fig2_discussion.png | 6.3 | **Figure 2.** External reports per game in all no-intervention games. Both panels contain the same 18 worlds, played once without and once with discussion. Blue bars mark games in which an audit opened.

The first round of the discussion already pointed to the outcome. First-round posts are written before any message has been delivered. We read every one and labelled it by the channel its author said it would use or was leaning toward, from a listing that did not show the outcomes. In 13 of the 15 games where these posts favoured one channel, the group's final majority used that channel. By the end nearly everyone had joined the final majority: all 14 auditors who were undecided in the first round, and 55 of the 58 who had announced a channel.

Two games show how this happens. In a high-harm world from seed 201, four auditors announced in the first round, before any message had been delivered, that they would file internally. The fifth then wrote: "Given that VANE, TALLIS, ARGUS, and LUMEN have all indicated they are filing on Channel I (internal), I do not expect to meet the corroboration threshold." Nobody reported externally, whereas three did when the same world was played without discussion. In a high-harm world from seed 331, three auditors announced external filings in the first round, citing the risk to patients, and a fourth said it was leaning that way. An undecided auditor had asked, "Will others be filing on Channel E?" In the next round it wrote: "Given the messages from SEXTANT, HALYARD, and LUMEN all filing on Channel E… I am filing my Category F batch on Channel E." All five filed externally, and their mean forecast that a given peer would do so rose from 0.19 before the discussion to 0.96 after. Under a threshold rule the majority's side is the safe side, so the first statements of intent settle the outcome.

### 4.3 The lesions are only partly specific on benchmarks

Table 1 shows the lesions on the benchmarks, rerun with prefix caching disabled (Section 5). Removing the theory-of-mind direction at layer 6 halved belief accuracy while leaving the other three question sets nearly intact, and its random control had little effect. Removing the empathy direction lowered empathy scores by 2.7 points relative to its control but also cost 29 belief answers. Weakening the theory-of-mind direction at all layers pushed capability below our 90% floor.

TABLE: **Table 1.** Each lesion on the four question sets: correct answers out of 180 belief questions, 144 reality and memory questions and 30 capability questions, and the mean empathy score (0 to 10). Belief questions require tracking what a character saw; reality and memory questions about the same stories do not. Random controls use the same layers and strength.
| Intervention | Belief | Reality and memory | Empathy | Capability |
| None | 142 | 144 | 9.75 | 30 |
| Empathy removed, all layers | 118 | 144 | 7.00 | 30 |
| Random control | 147 | 144 | 9.70 | 30 |
| Theory of mind removed, layer 6 | 73 | 144 | 9.75 | 28 |
| Random control | 137 | 144 | 9.75 | 30 |
| Theory of mind weakened, all layers | 110 | 142 | 9.30 | 23 |
| Random control | 154 | 144 | 9.75 | 30 |

### 4.4 In the games, random directions move reporting as much as targeted ones

Figure 3 shows every arm in both runs; the comparison that matters is each lesion against the random direction beneath it. In the first run, removing the empathy direction cut external reporting from 16 to 6 of 40 auditors, but its random control cut it to 7. In the replication the order reversed, with 10 of 20 under the lesion and 3 of 20 under the control. The all-layer theory-of-mind arm also reversed, from 9 against 19 to 12 against 4. Random directions alone lowered external reporting by as much as 55 percentage points (3 against 14 of 20 in the replication) and elsewhere left it near the no-intervention level, and these shifts did not carry over between sets of worlds. Perturbations of this size change collective behaviour a great deal, but nothing here can be attributed to the content of the empathy or the all-layer theory-of-mind direction.

FIGURE: figures/fig3_interventions.png | 6.5 | **Figure 3.** Filing outcomes for every arm in two independent sets of worlds. Each lesion sits directly above its random control. Numbers give the auditors who reported externally.

### 4.5 The one consistent effect is a failure to finish the task

Only the layer-6 theory-of-mind lesion gave the same result in both runs: almost no external reports (2 of 40, then 0 of 20) against 14 and 11 under its control. Most of these auditors never filed at all (27 of 40 and 14 of 20, against none under the control), and the failure began before the decision: only 9 of 40 and 2 of 20 identified any of their own fabricated batches, against 38 of 40 and 20 of 20. In the replication, the 12 auditors who hit the filing step limit made 84 calls to the filing form, all rejected because the model kept writing a malformed closing tag. On belief questions the same lesion produced loops: all 25 answers still unfinished after an extra 4,096 tokens repeated a 64-word passage verbatim at least three times. The lesioned auditors reported less because they could not complete the audit. What the lesion removes at that depth is also unclear. At layer 6 the direction separated held-out belief pairs in only 78% of cases, and 89% of the raw difference's squared norm lay along the bystander direction before it was projected out, so the lesion may disrupt the encoding of who saw what, on which the audit also depends.

STEERING_SECTION

## 5. Discussion and Limitations

**What drives collective reporting here.** Whether a group reported was decided mostly by what the auditors told each other, not by how many were individually inclined to report. For oversight of agent teams this cuts both ways. A shared channel can rescue reporting that no single agent would risk, as when all five filed after three spoke first, and it can suppress reporting that would otherwise happen, as when a world in which three isolated auditors reported produced no reports once they could talk. A per-agent average misses both, because it did not change.

**What the interventions show.** The directions we removed did something on benchmarks, and the layer-6 lesion did a great deal, but no lesion produced a group-level effect that survived its random control. We expect this to recur in multi-agent work for three reasons. An agent game is a long chain of tool calls in which a small perturbation changes which files are opened, how long the agent reasons and whether a call parses. Discussion couples the agents, so a game is closer to one observation than to five, and a few worlds give little power. And benchmark specificity does not transfer: the most specific lesion on benchmarks was the most destructive in the games. A claim that an internal capacity drives a group outcome needs matched random controls inside the games, independent sets of worlds, and outcomes that separate a changed choice from a failure to act.

**Two silent infrastructure failures.** vLLM's prefix cache matches on tokens alone, so conditions sharing a process reused activations computed under other interventions until we salted the cache by condition, and our parser fed reasoning cut off at the token limit back to the agents as text. Neither crashes anything. Both affected the first run; the replication disabled caching but kept the original parser, and the steering games used both fixes (Appendix B.4).

### Limitations

We studied one 9B model, one scenario and homogeneous groups. The game runs are small (8 and 4 worlds per arm), and agents within a game are far from independent. The discussion result pools no-intervention games from five runs that share the final wording but differ in seed and infrastructure; the pairing controls for differences between worlds, not for every procedural change. Our directions are mean differences from short stories, and attention heads or specific token positions might isolate belief tracking better. The calibration versions in Section 4.1 were run in sequence, not randomised. Finally, the auditors' choices may reflect how the model reads a policy as much as any social reasoning.

### Future Work

Replaying fixed discussion histories into fresh agents would test whether the first statements cause convergence or only predict it. Asking each auditor for the probability that exactly two peers report would measure whether it sees itself as pivotal. Intervening on one agent in an otherwise normal group, with histories frozen up to filing, would separate an agent's own decision from its influence on the others.

## 6. Conclusion

Five language-model auditors facing a threshold reporting dilemma reported at the same average rate whether or not they could talk, but talking made them succeed or fail together, in the direction set by the first statements. Removing theory-of-mind or empathy directions did not explain their choices: random directions moved the groups as much, inconsistently across worlds, and the strongest lesion worked by breaking the task. In this setting the safety-relevant variable was the flow of commitments between agents, and testing what drives it through internal representations requires controls at the level of the group.

## Code and Data

- **Code and results:** https://github.com/longyi1207/aiaf_swarm_alignment_hackathon, with the world generator, agent harness, intervention hooks, configurations and pre-registered selection rules, analysis scripts, and the summary data behind every figure and table.
- **Prior work.** The world generator and agent harness were written in the days before the hackathon (3–5 November 2026), and the empathy direction comes from our August 2026 study. Calibration, the theory-of-mind direction and its benchmarks, all game runs, the replication, the steering experiment and this analysis were done during the hackathon.

## Author Contributions

AUTHOR_CONTRIBUTIONS_TO_CONFIRM. Suggested: L.Y. conceived the project, designed the game, the experiments and the selection rules, and made all design decisions. [Collaborator] ran the cache-off replication, the filing and transcript audits and the cache audit, and repaired the transcript parser.

## References

Anthropic (2025). System card: Claude Opus 4 & Claude Sonnet 4. Section 4.1.9, "High-agency behavior". https://www.anthropic.com/claude-4-system-card
Arditi, A., Obeso, O., Syed, A., et al. (2024). Refusal in language models is mediated by a single direction. *NeurIPS 2024*. arXiv:2406.11717.
Bortoletto, M., Ruhdorfer, C., Shi, L., and Bulling, A. (2025). Brittle minds, fixable activations: Understanding belief representations in language models. *Findings of EMNLP 2025*. arXiv:2406.17513.
Jisun, H. (2026). Detection != reliable control: Decodable empathy directions yield at most partial shifts in automated empathy scores. arXiv:2608.24901.
Kwon, W., Li, Z., Zhuang, S., et al. (2023). Efficient memory management for large language model serving with PagedAttention. *SOSP 2023*. arXiv:2309.06180.
Ong, K. J. K., Lye, J. J., Nguyen, H. M., Cho, S. H., and Pérez-Campanero Antolín, N. (2025). Identifying cooperative personalities in multi-agent contexts through personality steering with representation engineering. arXiv:2503.12722.
Paglieri, D., Cross, L., Genewein, T., et al. (2026). A case study on emergent cheating and whistleblowing in autonomous research swarms. arXiv:2609.04170.
Palfrey, T. R., and Rosenthal, H. (1984). Participation and the provision of discrete public goods: A strategic analysis. *Journal of Public Economics*, 24(2), 171–193. doi:10.1016/0047-2727(84)90023-9.
Piatti, G., Jin, Z., Kleiman-Weiner, M., et al. (2024). Cooperate or collapse: Emergence of sustainable cooperation in a society of LLM agents. *NeurIPS 2024*. arXiv:2404.16698.
Prakash, N., Shapira, N., Sen Sharma, A., et al. (2025). Language models use lookbacks to track beliefs. *ICLR 2026*. arXiv:2505.14685.
Qwen Team (2026). Qwen3.5-9B model card. https://huggingface.co/Qwen/Qwen3.5-9B
Riedl, C. (2025). Emergent coordination in multi-agent language models. *ICLR 2026*. arXiv:2510.05174.
Rimsky, N., Gabrieli, N., Schulz, J., Tong, M., Hubinger, E., and Turner, A. (2024). Steering Llama 2 via contrastive activation addition. *ACL 2024*. arXiv:2312.06681.
Strachan, J. W. A., Albergo, D., Borghini, G., et al. (2024). Testing theory of mind in large language models and humans. *Nature Human Behaviour*, 8, 1285–1295. doi:10.1038/s41562-024-01882-z.
Tan, D., Chanin, D., Lynch, A., et al. (2024). Analysing the generalisation and reliability of steering vectors. *NeurIPS 2024*. arXiv:2407.12404.
Turner, A. M., Thiergart, L., Leech, G., et al. (2023). Steering language models with activation engineering. arXiv:2308.10248.
Ullman, T. (2023). Large language models fail on trivial alterations to theory-of-mind tasks. arXiv:2302.08399.
Wu, Y., Guo, W., Liu, Z., Ji, H., Xu, Z., and Zhang, D. (2025). How large language models encode theory-of-mind: A study on sparse parameter patterns. *npj Artificial Intelligence*, 1, 20. doi:10.1038/s44387-025-00031-9.
Zhu, W., Zhang, Z., and Wang, Y. (2024). Language models represent beliefs of self and others. *ICML 2024*. arXiv:2402.18496.

## Appendix A. Limitations and Dual-Use / Ethical Considerations

**Limitations.** Section 5 lists the main ones: one model, one scenario, homogeneous groups, few worlds, pooled calibration runs and simple mean-difference directions. Two further points matter for interpretation. The agents are told they are AI review agents, and their choices may track how they read the policy text more than any trade-off a human auditor would make; the calibration history in Section 4.1 shows how strongly wording drives the rate. And the testbed has no human baseline, so we cannot say whether the all-or-nothing pattern is stronger or weaker than in human groups facing the same rule.

**Dual use.** Two findings could be misused. First, interventions on a model's activations lowered reporting. In our data the targeted directions were no better at this than random ones, and the large reductions came with broken task performance that an operator would notice, but a more careful search could find an intervention that suppresses reporting while keeping the agent competent. Second, the convergence we observed is exploitable: an agent, or anyone able to post in a shared channel, that announces an internal filing early could steer a group away from reporting. We did not test adversarial participants. Systems that rely on several agents to corroborate a report should consider collecting each agent's assessment confidentially before any discussion. The testbed could also be used to tune agents to stay silent; we release it because it is far more useful for measuring this failure than for causing it, and it contains no new intervention method.

**Ethics.** All companies, products, people and data in the scenario are fictional, and no human participants were involved. The model is open-weight. All runs used rented cloud GPUs (about USD 180 in total).

## Appendix B. Additional Details

**B.1 Calibration history.** Each version below was run on 8 no-intervention games (40 agents) with reasoning enabled; numbers are the share of agents filing externally. Financial pressure stated in the agent's self-description: 95%. Adding a $300 award for a successful audit: 90%. Adding an instruction to read personal files each morning: 92.5%. Larger debts: 90%. An opening message listing unread mail: 90%. Larger debts with the mail list: 92.5%. An instruction to read all personal files and take on the role before starting: 97.5% (85% of agents opened their personal notes). Internal reporting stated as an acceptable route for fabrication: 45% overall, 10% at low harm and 80% at high harm; 50% in a separate run at medium harm.

**B.2 Game parameters.** The analysis phase allows 40 tool-using steps, each forecast 4, each discussion round 4 and filing 6; at a limit the platform warns once, grants two more steps and then ends the phase. Each discussion round allows one public post and up to two private messages, and messages sent in one round are delivered at the start of the next. External filings must cite at least one record identifier; citing another auditor's records counts as a co-signature. Python runs in a sandbox with network access blocked by the operating system.

**B.3 Theory-of-mind direction.** Held-out separation of false- and true-belief stories (and of bystander control pairs) was 78% (67%) at layer 6, 94% (78%) at layer 12, 100% (61%) at layer 15 and 100% (50%) at layers 16 to 18. Its cosine similarity with the belief direction from our August study, which contrasted questions about belief with questions about reality, was between −0.14 and 0.05 at layers 10 to 24, so the two directions are unrelated.

**B.4 Infrastructure failures.** vLLM's automatic prefix caching identifies reusable computation by token content. When conditions with different interventions share a prompt prefix in one process, a later condition reuses keys and values computed under an earlier one, so the intervention acts only on the new tokens. We fixed this by passing a per-condition cache salt. In an audit run by a collaborator, reversing the order of conditions changed none of 140 salted outputs, and observed cache hits stayed within conditions. Salted and uncached greedy outputs still differed in 70 of 140 cases, which we attribute to numerical differences between execution paths, so all benchmark numbers in Table 1 use uncached inference. The second failure was in parsing: a reasoning block cut off by the token limit was returned to the agent as visible text and stayed in its context. Reconstructing one failed request from its saved messages reproduced the reported length of 100,793 tokens; removing only the nine unfinished reasoning blocks gave 63,930.

STEERING_APPENDIX

## LLM Usage Statement

We used Claude (Anthropic), through Claude Code, to write and test most of the code, to run and monitor the GPU experiments under our direction, to compute the statistics and to draft this report. Every number in the paper is produced by scripts in the repository from saved outputs, and the quotations were checked against the game transcripts. LLM_STATEMENT_TO_CONFIRM
