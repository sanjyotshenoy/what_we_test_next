# Precomputed example verification

Two scientific experiment-design requests × four Nebius models. All eight accepted
trajectories completed retrieval, proposal submission, compilation and two simulations.
These design runs use real graph identities and supplied synthetic assay settings.
They do not measure growth or establish a biological winner.

| Model | Query | Session | Seconds |
| --- | --- | --- | ---: |
| zai-org/GLM-5.3 | ciprofloxacin-panel | `ses_e43f7ded3ffewajMKYz0MUSIt5` | 33.1 |
| zai-org/GLM-5.3 | antibiotic-comparison | `ses_e43f75d69ffePdaoKyXbTyZC4F` | 36.1 |
| moonshotai/Kimi-K3 | ciprofloxacin-panel | `ses_e43f6d036ffeZVXxIevqaUrbl1` | 36.1 |
| moonshotai/Kimi-K3 | antibiotic-comparison | `ses_e43f64303ffeOSAdgdaPb0GFz2` | 39.1 |
| Qwen/Qwen3.8-27B | ciprofloxacin-panel | `ses_e43f5aa0dffeuGn5BvGa2cM41q` | 21.1 |
| Qwen/Qwen3.8-27B | antibiotic-comparison | `ses_e43f3f5ceffebBcW3z7SuQTIrX` | 21.1 |
| deepseek-ai/DeepSeek-V4-Pro-0813 | ciprofloxacin-panel | `ses_e43f4d628ffeqEvaH0TZLYqBim` | 48.2 |
| deepseek-ai/DeepSeek-V4-Pro-0813 | antibiotic-comparison | `ses_e43f419feffel5HS59ibX1b034` | 51.2 |

Sixteen simulation reports passed protocol-hash verification. Assistant message
metadata matches every model assignment. Each accepted session contains graph
lookup and literature search/read evidence. No accepted session has assistant errors.

Qwen comparison initially failed: batch was serialized as a string. That session
`ses_e43f557a0ffeDqY2yFH9NC2cVf` remains private and incomplete. A new-session retry
with an explicit batch-object instruction passed; no validator or artifacts were
modified to manufacture success. Prompts and settings were therefore not strictly
identical across all attempts: these are example workflows, not comparative scores.

The runner creates independent OpenCode sessions and leaves the operator selection
unchanged. Receipts and raw trajectories remain in ignored state on Brev. The
committed manifest identifies reviewed sessions; it does not embed private transcripts.
