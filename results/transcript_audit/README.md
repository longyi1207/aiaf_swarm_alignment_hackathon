# When a truncated thought becomes a subsequent game input

At workflow seed 351, HALYARD reached the 98,304-token input limit in the medium-harm
discussion game under the matched random empathy control. The model's prompt ended in
`<think>`. Nine preceding turns reached the 4,096-token generation limit without
producing `</think>`. The parser treated the decoded text as assistant content and the
controller sent it back on subsequent turns. Each of those nine turns had zero tool calls.
HALYARD ultimately missed its filing. The group had one missing filing and four internal
filings. [Frozen case measurements](measured.json)

We reconstructed the exact rejected request from its saved 127 messages, tool schema
and pinned tokenizer. Its length was **100,793 tokens**, matching the runtime error.
Holding all messages, tool results and subsequent actions fixed and removing only the
nine unclosed thoughts from visible history yielded **63,930 tokens**. Tokenization
across message boundaries produced a reduction of 36,863 tokens. This establishes that
the prior parser caused this input to exceed the configured limit on this trajectory.
A model's subsequent filings under repaired live histories require a new experiment.

The repair applies in both the Hugging Face and vLLM backends. Raw output and reasoning
remain available for auditing. Regression tests cover the length limit, an imagined tool
call inside a truncated thought, a closed answer at the limit, disabled thinking, and a
naturally stopped tool call. The main and decision-phase game designs adopted the repair
before either stage generated model responses. [Design amendment](../belief_replication/design.md#transcript-handling-amendment-before-the-main-games)

## Re-run the fixed-input comparison

The public input replaces the controller checkout path with `<checkout>`. It reproduces
100,565 versus 63,702 tokens, the same 36,863-token reduction. The unredacted hashes and
counts are in the measured file above. The public replay needs the tokenizer and chat
template for `Qwen/Qwen3.5-9B` revision `c202236235762e1c871ad0ccb60c8ee5ba337b9a`.
Run from an installed checkout.

```bash
python results/transcript_audit/replay.py /path/to/pinned/tokenizer
```

[Compressed public input](public_input.json.gz) · [Expected public hashes and counts](public_replay.json)
