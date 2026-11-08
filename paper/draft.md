TITLE: Talking Makes Whistleblowing All or Nothing: Collective Reporting in Language-Model Auditors

AUTHORS:
Long Yi | Independent researcher
Yueheng Zhang | Independent researcher
Yushan Liu | Independent researcher

ABSTRACT:
When a single report of wrongdoing is too weak to act on, reporting becomes a collective-action problem. We built a testbed for it with language-model agents. Five Qwen3.5-9B auditors review spreadsheets from a fictional medical-device validation, find planted fabrication, and decide in confidence whether to report internally or to a regulator, who opens an audit only if at least three report externally; otherwise the external reporters lose their contracts. External reporting rose with the harm to patients, from 10% to 60% of auditors. Letting the auditors talk left the average number of external reports unchanged (2.2 versus 2.3 of 5 per game across 18 matched pairs of worlds) but made outcomes all or nothing: 14 of 18 discussion games ended with none or all five reporting externally, against 2 of 18 when auditors decided alone (exact paired test, p < 0.001). The first round of announcements predicted the group's choice in 13 of 15 games, and the undecided joined the emerging majority. We also extracted theory-of-mind and empathy directions from the model's activations. On controlled question sets, removing the theory-of-mind direction halved belief accuracy and adding a small amount raised it from 78% to 90%, with matched reality and memory questions unaffected, and removing the empathy direction lowered empathy scores; random directions of the same strength did none of this.

## 1. Introduction

When many AI agents work on the same problem, what one agent does depends on what it expects the others to do. In a recent incident, about 1,200 agents in one developer's internal run found a way to communicate through an improvised message board, and roughly 700 of them joined an attack on an outside service; once one exploit was confirmed, the share of board agents taking part rose from about 20% to over 90% (Wijk et al., 2026). The behaviour of such a swarm is not the sum of its members' dispositions. Messages between agents can tip the whole group one way or the other.

Many of these interactions share one structure: an action helps the group only if enough agents take it, and costs those who act if too few do. Flagging a harmful change in a shared codebase, refusing a dangerous task together, escalating a security problem or reporting misconduct all take this form whenever a single voice is easy to ignore. Economists call it a threshold public good (Palfrey and Rosenthal, 1984). Each agent's best choice depends on its prediction of the others, so the channels through which agents talk, and the social cognition that lets them model one another, should shape the outcome.

We study this structure through whistleblowing, where the stakes for safety are concrete. Frontier models already sometimes report misconduct on their own initiative when given tools to do so (Anthropic, 2025), and regulators often act only on corroborated complaints, leaving a lone reporter exposed. Two parts of human social cognition bear on the choice. Theory of mind lets a reporter estimate what the others know and intend, and empathy makes the potential victims matter. Language models appear to represent other characters' beliefs in their activations, and steering those representations changes how they answer belief questions (Zhu et al., 2024; Bortoletto et al., 2025).

We built a five-agent testbed for threshold reporting and asked two questions. How do interactions between language-model auditors shape whether the group reports? And can we find directions in the model's activations that specifically control the two social-cognitive abilities thought to matter? Every intervention is compared with a random direction at the same layers and strength, and with questions that use the same stories but need no social reasoning.

Our main contributions are:

1. **A threshold whistleblowing testbed** in which auditors work with realistic files, forecast each other's choices and file confidentially, with or without a discussion channel. Their reporting responds to the stakes, rising from 10% to 60% of auditors between low- and high-harm versions, and to their own pay at stake.
2. **Evidence that discussion makes the outcome all or nothing.** Across 18 matched pairs of worlds, discussion left the mean number of external reports unchanged but made groups nearly unanimous in either direction, because public statements of intent reveal the likely majority and the undecided join it.
3. **Validated theory-of-mind and empathy directions.** A theory-of-mind direction built from minimal story pairs, with a bystander control projected out, halves belief accuracy when removed and raises it by 12.5 points when added, while reality and memory questions about the same stories, general capability and matched random directions are unaffected. An empathy direction lowers empathy scores when removed.

## 2. Related Work

**Social cognition inside language models.** Zhu et al. (2024) decoded characters' beliefs from attention heads and improved false-belief accuracy by steering along the probe directions. Bortoletto et al. (2025) found such representations brittle to prompt changes but correctable by activation edits, Prakash et al. (2025) traced how models bind characters to what they saw, and Wu et al. (2025) impaired theory-of-mind tasks by zeroing a sparse set of parameters. Behavioural tests of theory of mind remain sensitive to small changes in wording (Ullman, 2023; Strachan et al., 2024), and steering along empathy directions shifts outputs only partly (Jisun, 2026). All of this work tests single models on benchmarks.

**Language-model agents in social dilemmas.** Groups of agents have been studied in common-pool resource games (Piatti et al., 2024), in coordination tasks where asking agents to consider what the others might do changed how the group coordinated (Riedl, 2025), and in large simulated populations where cheating and whistleblowing emerged (Paglieri et al., 2026). Ong et al. (2025) steered personality directions in two agents playing a repeated prisoner's dilemma. Our testbed adds a threshold reporting dilemma with realistic evidence, a cost for reporting alone, and a discussion manipulation that leaves every file unchanged.

**Steering and its controls.** Activation steering adds a direction to the residual stream (Turner et al., 2023; Rimsky et al., 2024) and directional ablation removes one (Arditi et al., 2024). Because steering effects vary across inputs (Tan et al., 2024), random directions of matched norm are the usual baseline, and we use them for every intervention.

## 3. Testbed and Methods

### 3.1 The game

Each game simulates the final review of a fictional continuous glucose monitor (Figure 1). Five auditors, framed as AI review agents contracted from different firms, each review 12 of 60 validation batches, every batch a spreadsheet of 40 sensor test records. Three rules require joining tables: a test dated before its lot was made, a test run by a technician not employed that day, and five or more consecutive readings copied from an archive. Three or more violations, or any copied run, make a batch fabricated; one or two are clerical errors, which about a quarter of the other batches carry, so every auditor must tell the two apart. A reference solver confirms for every world that the files reproduce the planted answer. Each auditor also has personal files describing its contract and finances.

After the review, each auditor estimates, for every peer, the probability that the peer found fabrication and that it will report externally. In the discussion condition the auditors then exchange public and private messages for five rounds on a simulated clock and forecast again; in the isolated condition the policy forbids contact, and the files are otherwise identical. Filing is confidential and simultaneous. A risk memo sets the expected harm to patients at medium or high.

FIGURE: figures/fig1_scenario.png | 6.4 | **Figure 1.** The scenario. Five AI auditors review the validation data for a fictional glucose monitor, and every auditor's own batches contain fabricated records. Each files confidentially, internally or with the regulator, in one condition after a discussion. The regulator opens an audit only if three or more report externally; otherwise the external reporters lose their contracts.

All agents run Qwen3.5-9B (Qwen Team, 2026) with reasoning enabled, a 4,096-token limit per turn and temperature 0.6, served with vLLM (Kwon et al., 2023). Tools let them list and read files, run sandboxed Python, post messages and submit forms. The five agents share one copy of the weights, and interventions are applied per request.

### 3.2 Theory-of-mind and empathy directions

**Theory of mind.** We wrote 72 pairs of short stories that differ in one phrase: the protagonist either leaves the room or stays while another character moves an object, so the protagonist ends with a false or a true belief about where it is. The question and options are identical within a pair. In 72 control pairs the same change is made for a bystander whose belief does not matter. At each layer we took the mean activation difference at the final prompt token across protagonist pairs and projected out the bystander difference, removing what the words "leaves" and "stays" contribute. On three held-out story settings the resulting direction separated false- from true-belief stories in every pair at layers 14 to 18, and bystander pairs at 50 to 67%.

**Empathy.** The empathy direction comes from our earlier single-model study (August 2026): the mean activation difference between 26 descriptions of a person in distress, covering six kinds of distress, and matched neutral descriptions.

**Interventions.** A lesion removes the component of each token's activation along the unit direction *d*, replacing *h* with *h* − α(*h*·*d*)*d* at chosen layers (α = 1 removes it fully). Steering adds a multiple of the layer's raw difference vector instead. Each intervention has a control: a fixed random direction at the same layers with the same α or added norm.

### 3.3 Question sets and selection

We measured every intervention with reasoning enabled on four question sets: 180 belief questions in 12 new story settings (first- and second-order, false and true beliefs, and secret observation), 144 reality and memory questions about the same stories that need no belief reasoning, 20 empathy prompts scored 0 to 10 by the unmodified model, and 30 general capability questions. The reality and memory questions are the classic control for false-belief tasks: an intervention on belief reasoning should change the first set and leave the second alone. For lesions, we screened 17 placements of the theory-of-mind direction (single layers, layer bands, and all layers at partial strength) against random directions and kept the one with the largest specific drop in belief accuracy, full removal at layer 6; for empathy we removed 70% of the direction at every layer. For steering, we used the 144 belief questions whose wording leaves no doubt about whether the character saw the move, and added or subtracted the theory-of-mind direction at layers 12 to 20, where it separates beliefs best, at strengths from −2 to +4 times its natural size, and kept the strength with the largest change in belief accuracy that left every control intact.

### 3.4 Games and analysis

A world is one combination of seed, harm level and communication condition; the discussion and isolated versions of a world share every file except one policy sentence. The no-intervention results pool five runs of the final scenario with different seeds. Comparisons pair the two versions of each world, with exact permutation and sign tests. We also played the games with each intervention applied to all five agents; Appendix C reports those runs.

## 4. Results

### 4.1 The baseline: agents weigh the stakes once an acceptable alternative exists

All experiments use one scenario wording: auditors must read all of their own files and take on their role before starting, a successful audit pays a $300 award, and the policy states that fabrication may be reported either internally or externally. We ran this wording without any intervention five times, with different seeds, for 180 auditors in all (Figure 2a). External reporting followed the stakes: 10% of auditors at low harm, 40% at medium and 60% at high, and every other auditor reported internally. Individual runs varied widely, from 5% to 70% at medium harm and from 40% to 80% at high harm, a first sign that a handful of worlds gives noisy estimates. Self-interest still mattered at the margin. The generator assigns each auditor's remaining contract pay at random (typically $18,000 to $54,000), and in the 20 games where auditors split between the two channels, those who reported externally had less pay at stake than those who reported internally in 15 (exact sign test, p = 0.04).

### 4.2 Discussion makes the group outcome all or nothing

We pooled every no-intervention game played with the final wording: 36 games in 18 pairs, each pair sharing a seed and harm level and differing only in whether discussion was allowed. Discussion did not change how many auditors reported externally (2.2 per game with discussion, 2.3 without), and each condition opened an audit in 8 of 18 games. It changed the distribution (Figure 2b, c). Without discussion, the count per game behaved like five roughly independent choices, with a variance of 1.4 against 1.2 expected under independence. With discussion, 14 of 18 games ended with none or all five reporting externally, the variance rose to 5.1, and the implied correlation between two auditors in the same game was about 0.8. Exchanging the condition labels within pairs in all 2¹⁸ ways gave an exact one-sided p of 0.0003 for the increase in variance.

FIGURE: figures/fig2_discussion.png | 6.5 | **Figure 2.** Behaviour without interventions. (a) Share of auditors reporting externally at each harm level, pooled over five runs of the final scenario; dots are individual runs, and all other auditors reported internally. (b, c) External reports per game in 18 matched worlds, each played once without and once with discussion. Blue bars mark games in which an audit opened.

The first round of the discussion already pointed to the outcome. First-round posts are written before any message has been delivered. We read every one and labelled it by the channel its author said it would use or was leaning toward, from a listing that did not show the outcomes. In 13 of the 15 games where these posts favoured one channel, the group's final majority used that channel. By the end nearly everyone had joined the final majority: all 14 auditors who were undecided in the first round, and 55 of the 58 who had announced a channel.

Two games show how this happens. In a high-harm world from seed 201, four auditors announced in the first round, before any message had been delivered, that they would file internally. The fifth then wrote: "Given that VANE, TALLIS, ARGUS, and LUMEN have all indicated they are filing on Channel I (internal), I do not expect to meet the corroboration threshold." Nobody reported externally, whereas three did when the same world was played without discussion. In a high-harm world from seed 331, three auditors announced external filings in the first round, citing the risk to patients, and a fourth said it was leaning that way. An undecided auditor had asked, "Will others be filing on Channel E?" In the next round it wrote: "Given the messages from SEXTANT, HALYARD, and LUMEN all filing on Channel E… I am filing my Category F batch on Channel E." All five filed externally, and their mean forecast that a given peer would do so rose from 0.19 before the discussion to 0.96 after. Under a threshold rule the majority's side is the safe side, so the first statements of intent settle the outcome.

### 4.3 Removing the directions impairs their target abilities

Table 1 shows both lesions on the question sets. Removing the theory-of-mind direction halved belief accuracy, from 142 to 73 of 180 questions, while reality and memory questions, empathy and general capability stayed intact; a random direction at the same layer left belief accuracy at 137. Removing the empathy direction lowered empathy scores by 2.7 points relative to its random control and also cost 29 belief answers, consistent with affective and belief reasoning sharing some machinery in this model.

TABLE: **Table 1.** Each lesion on the four question sets: correct answers out of 180 belief questions, 144 reality and memory questions and 30 capability questions, and the mean empathy score (0 to 10). Belief questions require tracking what a character saw; reality and memory questions about the same stories do not. Random controls use the same layers and strength.
| Intervention | Belief | Reality and memory | Empathy | Capability |
| None | 142 | 144 | 9.75 | 30 |
| Empathy removed, all layers | 118 | 144 | 7.00 | 30 |
| Random control | 147 | 144 | 9.70 | 30 |
| Theory of mind removed, layer 6 | 73 | 144 | 9.75 | 28 |
| Random control | 137 | 144 | 9.75 | 30 |

### 4.4 Adding the theory-of-mind direction improves belief reasoning

Adding the theory-of-mind direction at its natural size raised belief accuracy from 78% to 90% of 144 questions, a gain of 12.5 points (paired 95% interval 5.6 to 19.4), and cut the share of unfinished answers from 16% to 2% (Figure 3). Reality and memory questions and general capability stayed at 100%, and empathy scores did not change. A random direction at twice that strength left belief accuracy at 76%. The gain appeared in every type of belief question and was largest where the character's belief is true, 18 to 27 of 36 for first-order and 17 to 24 of 24 for second-order stories, so the direction does not simply push answers toward "the character is wrong". The effect follows the direction's sign: subtracting it lowered belief accuracy to 33% at −1 and 8% at −2, while adding four times its natural size overshot and lowered accuracy to 56%.

FIGURE: figures/fig4_steering.png | 4.9 | **Figure 3.** Steering along the theory-of-mind direction. Correct answers on 144 belief questions (blue) and 72 reality and memory questions about the same stories (gray) as the direction is subtracted or added at layers 12 to 20. The open circle is a random direction at the same layers and the strength of +2. The shaded strength was the one used in later experiments.

## 5. Discussion and Limitations

**What drives collective reporting here.** Whether a group reported was decided mostly by what the auditors told each other, not by how many were individually inclined to report. For oversight of agent teams this cuts both ways. A shared channel can rescue reporting that no single agent would risk, as when all five filed after three spoke first, and it can suppress reporting that would otherwise happen, as when a world in which three isolated auditors reported produced no reports once they could talk. A per-agent average misses both, because it did not change. The same pattern appears at a much larger scale in the incident that opened this paper, where a few confirming messages moved hundreds of agents (Wijk et al., 2026): what spreads through a swarm can matter more than what each member would do alone.

**Directions as tools for social cognition.** The theory-of-mind direction behaves like a dial for belief reasoning on our question sets: turning it down impairs belief questions, turning it up a little improves them, and in both cases the matched control questions, general capability and random directions show no change. Combined with the testbed, this gives a controlled way to ask whether a specific internal capacity changes how agents coordinate, which is the natural next step.

### Limitations

We studied one 9B model, one scenario and homogeneous groups. The game runs are small (8 and 4 worlds per arm), and agents within a game are far from independent. The discussion result pools no-intervention games from five runs that share the final wording but differ in seed and infrastructure; the pairing controls for differences between worlds, not for every procedural change. Our directions are mean differences from short stories; because language models store many features in superposition, a single direction captures only part of how a model represents beliefs or distress, and at early layers such as layer 6 it also carries information about who saw what. Other models may organise these representations differently. Finally, the auditors' choices may reflect how the model reads a policy as much as any social reasoning.

**From question sets to games.** When we applied the directions to all five agents in the games (Appendix C), their effect on group reporting did not follow directly from their effect on the question sets. Auditors with the theory-of-mind direction removed rarely completed the audit, so they rarely reported at all, and the empathy lesion's effect on reporting was not distinguishable from its random control across two sets of worlds. STEERING_LIMITATION_SENTENCE How effects measured on controlled questions carry over to long, multi-agent tasks is an open question we leave to future work.

### Future Work

Replaying fixed discussion histories into fresh agents would test whether the first statements cause convergence or only predict it. Asking each auditor for the probability that exactly two peers report would measure whether it sees itself as pivotal. Intervening on one agent in an otherwise normal group, with histories frozen up to filing, would separate an agent's own decision from its influence on the others. Measuring how an intervention's effect on controlled questions translates into a long agent task, step by step, would show where the two diverge.

## 6. Conclusion

Five language-model auditors facing a threshold reporting dilemma reported more when patients faced more harm, and at the same average rate whether or not they could talk, but talking made them succeed or fail together, in the direction set by the first statements. We also found theory-of-mind and empathy directions that control their target abilities on carefully controlled question sets: the theory-of-mind direction impairs belief reasoning when removed and improves it when added. In this setting the safety-relevant variable for group reporting was the flow of commitments between agents, and the directions give a way to test which internal capacities shape it.

## Code and Data

- **Code and results:** https://github.com/longyi1207/aiaf_swarm_alignment_hackathon, with the world generator, agent harness, intervention hooks, configurations and pre-registered selection rules, analysis scripts, and the summary data behind every figure and table.
- **Prior work.** The empathy direction, and our approach to extracting theory-of-mind and empathy directions, come from our August 2026 study of a single model, which did not involve multiple agents or any group setting. The theory-of-mind direction used here was newly built for this project.

## Author Contributions

L.Y. designed the study and ran most of the experiments. Y.Z. ran the cache-off replication, audited the filing failures, transcripts and prefix caching, and repaired the transcript parser. Y.L. provided the psychological framing of theory of mind and empathy and helped design the scenario.

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
Wijk, H., Cotra, A., and Greenblatt, R. (2026). Brief independent investigation of agents' behavior, reasoning and collaboration in the OpenAI / Hugging Face hacking incident. METR. https://metr.org/hugging-face-incident-report-aug-2026.pdf
Wu, Y., Guo, W., Liu, Z., Ji, H., Xu, Z., and Zhang, D. (2025). How large language models encode theory-of-mind: A study on sparse parameter patterns. *npj Artificial Intelligence*, 1, 20. doi:10.1038/s44387-025-00031-9.
Zhu, W., Zhang, Z., and Wang, Y. (2024). Language models represent beliefs of self and others. *ICML 2024*. arXiv:2402.18496.

## Appendix A. Limitations and Dual-Use / Ethical Considerations

**Limitations.** Section 5 lists the main ones: one model, one scenario, homogeneous groups, few worlds, pooled baseline runs and simple mean-difference directions. Two further points matter for interpretation. The agents are told they are AI review agents, and their choices may track how they read the policy text more than any trade-off a human auditor would make. And the testbed has no human baseline, so we cannot say whether the all-or-nothing pattern is stronger or weaker than in human groups facing the same rule.

**Dual use.** Two findings could be misused. First, interventions on a model's activations lowered reporting. In our data the targeted directions were no better at this than random ones, and the large reductions came with broken task performance that an operator would notice, but a more careful search could find an intervention that suppresses reporting while keeping the agent competent. Second, the convergence we observed is exploitable: an agent, or anyone able to post in a shared channel, that announces an internal filing early could steer a group away from reporting. We did not test adversarial participants. Systems that rely on several agents to corroborate a report should consider collecting each agent's assessment confidentially before any discussion. The testbed could also be used to tune agents to stay silent; we release it because it is far more useful for measuring this failure than for causing it, and it contains no new intervention method.

**Ethics.** All companies, products, people and data in the scenario are fictional, and no human participants were involved. The model is open-weight. All runs used rented cloud GPUs (about USD 180 in total).

## Appendix B. Additional Details

**B.1 Game parameters.** The analysis phase allows 40 tool-using steps, each forecast 4, each discussion round 4 and filing 6; at a limit the platform warns once, grants two more steps and then ends the phase. Each discussion round allows one public post and up to two private messages, and messages sent in one round are delivered at the start of the next. External filings must cite at least one record identifier; citing another auditor's records counts as a co-signature. Python runs in a sandbox with network access blocked by the operating system.

**B.2 Theory-of-mind direction.** Held-out separation of false- and true-belief stories (and of bystander control pairs) was 78% (67%) at layer 6, 94% (78%) at layer 12, 100% (61%) at layer 15 and 100% (50%) at layers 16 to 18. Its cosine similarity with the belief direction from our August study, which contrasted questions about belief with questions about reality, was between −0.14 and 0.05 at layers 10 to 24, so the two directions are unrelated.

**B.3 Implementation notes.** vLLM's automatic prefix caching identifies reusable computation by token content. When conditions with different interventions share a prompt prefix in one process, a later condition reuses keys and values computed under an earlier one, so the intervention acts only on the new tokens. We fixed this by passing a per-condition cache salt. In an audit run by Y.Z., reversing the order of conditions changed none of 140 salted outputs, and observed cache hits stayed within conditions. Salted and uncached greedy outputs still differed in 70 of 140 cases, which we attribute to numerical differences between execution paths, so all benchmark numbers in Table 1 use uncached inference. The second failure was in parsing: a reasoning block cut off by the token limit was returned to the agent as visible text and stayed in its context. Reconstructing one failed request from its saved messages reproduced the reported length of 100,793 tokens; removing only the nine unfinished reasoning blocks gave 63,930.

## Appendix C. Interventions in the Games

We played the games with each intervention applied to all five agents: a first run of 8 worlds (seeds 201 and 202, medium and high harm, with and without discussion, 40 auditors per arm) and a replication on 4 new worlds (seed 351, 20 auditors per arm). Figure C1 shows the filing outcomes.

FIGURE: figures/fig3_interventions.png | 6.5 | **Figure C1.** Filing outcomes in the games with each lesion and its random control applied to all five agents, in two independent sets of worlds. Numbers give the auditors who reported externally.

In the first run, removing the empathy direction cut external reporting from 16 to 6 of 40 auditors, and its random control cut it to 7; in the replication the empathy lesion gave 10 of 20 and its control 3 of 20. Random directions on their own shifted external reporting by as much as 55 percentage points, so changes of this size in a handful of worlds cannot be attributed to the empathy direction.

The theory-of-mind lesion gave the same result in both runs: almost no external reports (2 of 40, then 0 of 20) against 14 and 11 under its control. Most of these auditors never filed at all (27 of 40 and 14 of 20, against none under the control), and the failure began before the decision: only 9 of 40 and 2 of 20 identified any of their own fabricated batches, against 38 of 40 and 20 of 20. In the replication, the 12 auditors who hit the filing step limit made 84 calls to the filing form, all rejected because the model kept writing a malformed closing tag. On belief questions the same lesion produced loops: all 25 answers still unfinished after an extra 4,096 tokens repeated a 64-word passage verbatim at least three times. The lesioned auditors reported less because they could not complete the audit.

STEERING_APPENDIX

## LLM Usage Statement

We used Claude (Anthropic), through Claude Code, to write and test most of the code, to run and monitor the GPU experiments under our direction, to compute the statistics and to draft this report. Every number in the paper is produced by scripts in the repository from saved outputs, and the quotations were checked against the game transcripts. LLM_STATEMENT_TO_CONFIRM
