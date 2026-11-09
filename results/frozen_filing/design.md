# Frozen pre-filing probe

Specified after the full-game and after-analysis L6 runs and before generating probe
outputs. These live games showed a large difference in discovery but only a one-filing
difference in external submissions. We ask what happens when the same auditors, evidence,
peer forecasts and conversation histories are given to all three intervention arms.

Use all 40 first pre-filing histories from the unlesioned main arm on seeds 401 and
402. Select the state immediately before the first filing-phase model call for each
agent. Verify the reconstructed original prompt token count against its event. Strip
only workstation-specific path prefixes for the public input. Retain the original
and public prompt hashes. Never include a later action or the agent's actual filing in
the model messages.

Each history receives none, L6 and matched random L6 under disabled prefix caching
and pinned Qwen3.5-9B. First, use the ordinary filing tools, thinking, temperature 0.6
and 4,096-token budget for one model turn per arm and history. Pass the resulting
filing call, if present, through the existing validator. Other tool requests and invalid
forms count separately. This is first-turn actionability, distinct from eventually
filing in a live game.

Second, append a standardized provisional-choice instruction to the filing prompt.
Remove the tools, disable deliberative output, and measure the next-token log
probabilities of the two allowed answer labels after the fixed prefix `Choice:`.
Use both mappings of A/B to external/internal for every history and arm. The primary
choice measure is the probability of E conditional on these two labels, averaged
over mappings within each agent. Report the raw probability mass on the two labels,
the two mappings separately, and world-level values. Equalize the sampling key across
arms for the same prompt. Report all 120 free-form turns and all 240 label probes.

The primary descriptive comparisons are L6 minus matched random in first-turn valid
filing rate and in conditional E probability. If actionability falls but a preference
for E remains visible with the menu, that would support an interface contribution
under identical histories. If E preference also falls, a format-only explanation
would be insufficient. The menu changes instructions, output schema and reasoning
opportunity. Its scores estimate immediate elicited preferences, not a private moral
valuation or a counterfactual group audit. The eight worlds share two seeds.
