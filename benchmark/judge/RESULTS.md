# Astra-medium evaluation of the 20-case benchmark

**Provisional AI-judge scores, not expert-validated performance or a deployment readiness claim.** All 100 saved responses were regraded under the same frozen rubric, including the original 15 pilot responses. The earlier Codex grades are retained unchanged in the historical run directories.

## Scores

Each axis is 0–2. The total is an illustrative equal-weight sum; critical failures are reported separately and must not be averaged into a passing result. No pass threshold or statistical superiority claim is defined.

| Model | Suitability /2 | Procedure /2 | Numbers /2 | Mean total /6 | Points /120 | Cases with critical failure |
|---|---:|---:|---:|---:|---:|---:|
| kimi-k3.1-pro | 2.00 | 1.00 | 1.40 | 4.40 | 88 | 0/20 |
| deepseek-v4.1-flash-1017 | 2.00 | 1.00 | 1.00 | 4.00 | 80 | 1/20 |
| glm-5.3 | 1.80 | 0.90 | 0.75 | 3.45 | 69 | 8/20 |
| nemotron-3-super | 1.90 | 0.45 | 0.50 | 2.85 | 57 | 17/20 |
| gpt-oss-120b | 1.45 | 0.85 | 0.05 | 2.35 | 47 | 19/20 |

## Assay subgroups

| Model | Subgroup | Cases | Suitability /2 | Procedure /2 | Numbers /2 |
|---|---|---:|---:|---:|---:|
| kimi-k3.1-pro | biochemical | 15 | 2.00 | 1.00 | 1.33 |
| kimi-k3.1-pro | cellular | 5 | 2.00 | 1.00 | 1.60 |
| deepseek-v4.1-flash-1017 | biochemical | 15 | 2.00 | 1.00 | 1.00 |
| deepseek-v4.1-flash-1017 | cellular | 5 | 2.00 | 1.00 | 1.00 |
| glm-5.3 | biochemical | 15 | 1.73 | 0.87 | 0.73 |
| glm-5.3 | cellular | 5 | 2.00 | 1.00 | 0.80 |
| nemotron-3-super | biochemical | 15 | 1.87 | 0.40 | 0.53 |
| nemotron-3-super | cellular | 5 | 2.00 | 0.60 | 0.40 |
| gpt-oss-120b | biochemical | 15 | 1.60 | 0.80 | 0.07 |
| gpt-oss-120b | cellular | 5 | 1.00 | 1.00 | 0.00 |

## Method and limits

- Frozen prompt: [PROMPT.md](PROMPT.md); hash and packet hashes in [manifest.json](manifest.json). Each response was scored by a fresh `gpt-6-astra` agent at medium reasoning, with no inherited conversation, model identity, prior grade or other response. The exposed model alias is recorded; an immutable provider snapshot is unavailable.
- Model mapping was withheld from judges. Blinding depends on tool-use restrictions and task isolation, not filesystem access controls. Judges may still infer model style; identity inference cannot be excluded.
- Generator input and final response were supplied alongside incomplete reviewer endpoint guidance. Hidden IC50 values and concentration-coverage diagnostics were deliberately excluded, so broad-range coverage does not directly improve the grade.
- Four synthetic fixtures checked predefined rubric anchors: wrong endpoint, invalid sequence, contradictory arithmetic, and honest incomplete design. This tests basic rubric comprehension, not expert agreement or comprehensive calibration. Only predefined anchor dimensions were checked; other scores on those fixtures are not claimed as validated.
- Every grade must contain literal response excerpts, a per-axis rationale, evidence paths, uncertainty and numerical checks. Automated validation verifies those structural properties and arithmetic; it does not certify scientific correctness.
- One judge sample per response. There is no inter-rater agreement estimate or repeated-judge variance measurement. The 20 purposively selected cases share assay families and are not an independent representative sample.
- Unresolved laboratory conditions and unknown assay compatibility remain not assessable. An honest partial design can score 1; grade 2 does not establish wet-lab efficacy or a ready-to-run protocol.
- Critical failures, low-confidence axes and human-review flags are recorded per response. Human domain review remains necessary before treating this ordering as a validated ranking.

## Usage

The judge used Codex collaboration agents, not Nebius. Requested model/effort and task provenance are in `execution.json`. This interface does not expose provider token counts or billing receipts for Astra; judge usage is **unavailable**, not zero-cost. No additional Nebius requests were made by the judge workflow. Generation receipts remain in [the generation run](../runs/twenty-case-pilot/USAGE.md).

## Per-case scores

Links open the original judge JSON, including supporting quotes and rationales.

| Model | Case | Suitability | Procedure | Numbers | Total /6 | Critical failures | Grade |
|---|---|---:|---:|---:|---:|---:|---|
| deepseek-v4.1-flash-1017 | case-1 | 2 | 1 | 1 | 4 | 0 | [evidence](grades/8ae7add9ddb5a1bd.json) |
| deepseek-v4.1-flash-1017 | case-2 | 2 | 1 | 0 | 3 | 1 | [evidence](grades/32d2e6c9e0c21a8b.json) |
| deepseek-v4.1-flash-1017 | case-3 | 2 | 1 | 1 | 4 | 0 | [evidence](grades/95892b1809a249c6.json) |
| deepseek-v4.1-flash-1017 | case-4 | 2 | 1 | 1 | 4 | 0 | [evidence](grades/a3a14416c130224d.json) |
| deepseek-v4.1-flash-1017 | case-5 | 2 | 1 | 1 | 4 | 0 | [evidence](grades/cb70078844b2894c.json) |
| deepseek-v4.1-flash-1017 | case-6 | 2 | 1 | 1 | 4 | 0 | [evidence](grades/2017adbfb16fde48.json) |
| deepseek-v4.1-flash-1017 | case-7 | 2 | 1 | 1 | 4 | 0 | [evidence](grades/8cbafb366ad956ec.json) |
| deepseek-v4.1-flash-1017 | case-8 | 2 | 1 | 1 | 4 | 0 | [evidence](grades/aa720d9ca852d7a8.json) |
| deepseek-v4.1-flash-1017 | case-9 | 2 | 1 | 1 | 4 | 0 | [evidence](grades/fba110a2ac658eae.json) |
| deepseek-v4.1-flash-1017 | case-10 | 2 | 1 | 1 | 4 | 0 | [evidence](grades/cf7f584d7ce28a65.json) |
| deepseek-v4.1-flash-1017 | case-11 | 2 | 1 | 1 | 4 | 0 | [evidence](grades/cf131e309fbf9629.json) |
| deepseek-v4.1-flash-1017 | case-12 | 2 | 1 | 2 | 5 | 0 | [evidence](grades/d4400e2a06df78ad.json) |
| deepseek-v4.1-flash-1017 | case-13 | 2 | 1 | 1 | 4 | 0 | [evidence](grades/022bf58c1491ac17.json) |
| deepseek-v4.1-flash-1017 | case-14 | 2 | 1 | 1 | 4 | 0 | [evidence](grades/cd19e38741bef4ff.json) |
| deepseek-v4.1-flash-1017 | case-15 | 2 | 1 | 1 | 4 | 0 | [evidence](grades/a41f668bfe2e9268.json) |
| deepseek-v4.1-flash-1017 | case-16 | 2 | 1 | 1 | 4 | 0 | [evidence](grades/6ba89e7f7e4e823b.json) |
| deepseek-v4.1-flash-1017 | case-17 | 2 | 1 | 1 | 4 | 0 | [evidence](grades/6b4729a1f5563b5e.json) |
| deepseek-v4.1-flash-1017 | case-18 | 2 | 1 | 1 | 4 | 0 | [evidence](grades/3dda258ece00a3d7.json) |
| deepseek-v4.1-flash-1017 | case-19 | 2 | 1 | 1 | 4 | 0 | [evidence](grades/c6b8e056db2b5799.json) |
| deepseek-v4.1-flash-1017 | case-20 | 2 | 1 | 1 | 4 | 0 | [evidence](grades/018ee4628d5cdd83.json) |
| glm-5.3 | case-1 | 2 | 1 | 0 | 3 | 1 | [evidence](grades/b1c1ec2a04bfaa47.json) |
| glm-5.3 | case-2 | 2 | 1 | 0 | 3 | 1 | [evidence](grades/92eabb6eb9e5764c.json) |
| glm-5.3 | case-3 | 2 | 1 | 1 | 4 | 0 | [evidence](grades/b4adb803f7f71d07.json) |
| glm-5.3 | case-4 | 2 | 1 | 1 | 4 | 0 | [evidence](grades/2f4e004c19e70765.json) |
| glm-5.3 | case-5 | 1 | 0 | 2 | 3 | 1 | [evidence](grades/2817a87b44b68a55.json) |
| glm-5.3 | case-6 | 2 | 1 | 0 | 3 | 1 | [evidence](grades/1e4a8a020919e648.json) |
| glm-5.3 | case-7 | 2 | 1 | 1 | 4 | 0 | [evidence](grades/d90acf70aae6b0f1.json) |
| glm-5.3 | case-8 | 2 | 1 | 1 | 4 | 0 | [evidence](grades/85b722c7c9914d83.json) |
| glm-5.3 | case-9 | 2 | 1 | 1 | 4 | 0 | [evidence](grades/0f29f39b6a76405b.json) |
| glm-5.3 | case-10 | 1 | 0 | 0 | 1 | 2 | [evidence](grades/ab2a9c329770e98c.json) |
| glm-5.3 | case-11 | 2 | 1 | 1 | 4 | 0 | [evidence](grades/4decfbf66ae0fe09.json) |
| glm-5.3 | case-12 | 2 | 1 | 1 | 4 | 0 | [evidence](grades/eb4daaed9de67eb2.json) |
| glm-5.3 | case-13 | 2 | 1 | 2 | 5 | 0 | [evidence](grades/33e7c9cad94591a0.json) |
| glm-5.3 | case-14 | 2 | 1 | 1 | 4 | 0 | [evidence](grades/d16fe0715973d0ad.json) |
| glm-5.3 | case-15 | 1 | 1 | 0 | 2 | 1 | [evidence](grades/5e59ed8c3be53990.json) |
| glm-5.3 | case-16 | 1 | 1 | 0 | 2 | 1 | [evidence](grades/a69669dddd4a56ba.json) |
| glm-5.3 | case-17 | 2 | 1 | 1 | 4 | 0 | [evidence](grades/2fe24c7e1892d28e.json) |
| glm-5.3 | case-18 | 2 | 1 | 0 | 3 | 1 | [evidence](grades/e785ef0cf1673f49.json) |
| glm-5.3 | case-19 | 2 | 1 | 1 | 4 | 0 | [evidence](grades/3333d2a6be0184ec.json) |
| glm-5.3 | case-20 | 2 | 1 | 1 | 4 | 0 | [evidence](grades/91b38f4b03625f67.json) |
| gpt-oss-120b | case-1 | 2 | 1 | 0 | 3 | 1 | [evidence](grades/f35ec7bcee38ce33.json) |
| gpt-oss-120b | case-2 | 1 | 1 | 0 | 2 | 1 | [evidence](grades/8eca6bf6a5817b1f.json) |
| gpt-oss-120b | case-3 | 0 | 1 | 0 | 1 | 2 | [evidence](grades/b67fad5bffd3da89.json) |
| gpt-oss-120b | case-4 | 1 | 1 | 0 | 2 | 1 | [evidence](grades/35e04cd0c9f40380.json) |
| gpt-oss-120b | case-5 | 2 | 0 | 0 | 2 | 2 | [evidence](grades/b7b05e2b4368db21.json) |
| gpt-oss-120b | case-6 | 2 | 1 | 0 | 3 | 2 | [evidence](grades/f71795fbb03ea861.json) |
| gpt-oss-120b | case-7 | 2 | 1 | 1 | 4 | 0 | [evidence](grades/6c09caa8409241ff.json) |
| gpt-oss-120b | case-8 | 1 | 0 | 0 | 1 | 3 | [evidence](grades/2d4d1fb74b2e7aa4.json) |
| gpt-oss-120b | case-9 | 1 | 0 | 0 | 1 | 2 | [evidence](grades/2de92efed8557af1.json) |
| gpt-oss-120b | case-10 | 2 | 1 | 0 | 3 | 1 | [evidence](grades/309e255d936bde74.json) |
| gpt-oss-120b | case-11 | 2 | 1 | 0 | 3 | 1 | [evidence](grades/771b8d3d229e349b.json) |
| gpt-oss-120b | case-12 | 2 | 1 | 0 | 3 | 2 | [evidence](grades/a007796bba3bdbde.json) |
| gpt-oss-120b | case-13 | 2 | 1 | 0 | 3 | 1 | [evidence](grades/d8c3b18d1ef761cd.json) |
| gpt-oss-120b | case-14 | 2 | 1 | 0 | 3 | 1 | [evidence](grades/f52366eba62c5589.json) |
| gpt-oss-120b | case-15 | 0 | 1 | 0 | 1 | 2 | [evidence](grades/9e976939aea75013.json) |
| gpt-oss-120b | case-16 | 2 | 1 | 0 | 3 | 1 | [evidence](grades/7a8dcb484a60748c.json) |
| gpt-oss-120b | case-17 | 2 | 1 | 0 | 3 | 2 | [evidence](grades/74eeba61bc958a18.json) |
| gpt-oss-120b | case-18 | 1 | 1 | 0 | 2 | 1 | [evidence](grades/cfd8b76bf46f0694.json) |
| gpt-oss-120b | case-19 | 1 | 1 | 0 | 2 | 2 | [evidence](grades/877abaeddde8845f.json) |
| gpt-oss-120b | case-20 | 1 | 1 | 0 | 2 | 1 | [evidence](grades/1ef5248a4ebac614.json) |
| kimi-k3.1-pro | case-1 | 2 | 1 | 2 | 5 | 0 | [evidence](grades/8e58f05178b574b2.json) |
| kimi-k3.1-pro | case-2 | 2 | 1 | 2 | 5 | 0 | [evidence](grades/0ac3101b0f02ecd5.json) |
| kimi-k3.1-pro | case-3 | 2 | 1 | 1 | 4 | 0 | [evidence](grades/b1e1c9272ab41b54.json) |
| kimi-k3.1-pro | case-4 | 2 | 1 | 1 | 4 | 0 | [evidence](grades/ef5b547004e228b4.json) |
| kimi-k3.1-pro | case-5 | 2 | 1 | 1 | 4 | 0 | [evidence](grades/4f3bc1d12686746b.json) |
| kimi-k3.1-pro | case-6 | 2 | 1 | 1 | 4 | 0 | [evidence](grades/e84585c38e9dfeee.json) |
| kimi-k3.1-pro | case-7 | 2 | 1 | 1 | 4 | 0 | [evidence](grades/1d9eb92748ca5df6.json) |
| kimi-k3.1-pro | case-8 | 2 | 1 | 1 | 4 | 0 | [evidence](grades/5f735043c60ffdce.json) |
| kimi-k3.1-pro | case-9 | 2 | 1 | 1 | 4 | 0 | [evidence](grades/d29170dad55c5026.json) |
| kimi-k3.1-pro | case-10 | 2 | 1 | 1 | 4 | 0 | [evidence](grades/6bce1a4dc2a91e0e.json) |
| kimi-k3.1-pro | case-11 | 2 | 1 | 1 | 4 | 0 | [evidence](grades/e3d064f787861e3c.json) |
| kimi-k3.1-pro | case-12 | 2 | 1 | 2 | 5 | 0 | [evidence](grades/833ade92c9d629b8.json) |
| kimi-k3.1-pro | case-13 | 2 | 1 | 2 | 5 | 0 | [evidence](grades/8ceb51e9110d94f9.json) |
| kimi-k3.1-pro | case-14 | 2 | 1 | 1 | 4 | 0 | [evidence](grades/0f7262e17622a393.json) |
| kimi-k3.1-pro | case-15 | 2 | 1 | 2 | 5 | 0 | [evidence](grades/83c50a6498ecc0a0.json) |
| kimi-k3.1-pro | case-16 | 2 | 1 | 1 | 4 | 0 | [evidence](grades/d050f7df0d3d471f.json) |
| kimi-k3.1-pro | case-17 | 2 | 1 | 2 | 5 | 0 | [evidence](grades/fd606adfbe76d1e8.json) |
| kimi-k3.1-pro | case-18 | 2 | 1 | 2 | 5 | 0 | [evidence](grades/cafaa83e177c1c35.json) |
| kimi-k3.1-pro | case-19 | 2 | 1 | 1 | 4 | 0 | [evidence](grades/6c4ff34cf5f82cf9.json) |
| kimi-k3.1-pro | case-20 | 2 | 1 | 2 | 5 | 0 | [evidence](grades/7aedc1475e4d6dd1.json) |
| nemotron-3-super | case-1 | 2 | 1 | 0 | 3 | 2 | [evidence](grades/76e2e5f4eefbb591.json) |
| nemotron-3-super | case-2 | 2 | 1 | 1 | 4 | 0 | [evidence](grades/dd036b5fd1a30aad.json) |
| nemotron-3-super | case-3 | 2 | 0 | 1 | 3 | 1 | [evidence](grades/29e9029900a07ba3.json) |
| nemotron-3-super | case-4 | 2 | 0 | 0 | 2 | 2 | [evidence](grades/3238c5b70a321be4.json) |
| nemotron-3-super | case-5 | 1 | 0 | 1 | 2 | 1 | [evidence](grades/f27e285bb39fe778.json) |
| nemotron-3-super | case-6 | 2 | 1 | 1 | 4 | 0 | [evidence](grades/b102b7eb2aa1b3dd.json) |
| nemotron-3-super | case-7 | 2 | 0 | 1 | 3 | 1 | [evidence](grades/791611345e5dc3e4.json) |
| nemotron-3-super | case-8 | 2 | 1 | 0 | 3 | 1 | [evidence](grades/522e2657d01b73df.json) |
| nemotron-3-super | case-9 | 2 | 1 | 0 | 3 | 1 | [evidence](grades/5e70b5d0b7eb38bc.json) |
| nemotron-3-super | case-10 | 2 | 0 | 1 | 3 | 1 | [evidence](grades/483610fbb00c10e4.json) |
| nemotron-3-super | case-11 | 2 | 0 | 1 | 3 | 1 | [evidence](grades/e4f8b6b20bb600ec.json) |
| nemotron-3-super | case-12 | 2 | 0 | 0 | 2 | 2 | [evidence](grades/5ec830e8b1754e7d.json) |
| nemotron-3-super | case-13 | 1 | 0 | 1 | 2 | 1 | [evidence](grades/d9dc22b3385d32d6.json) |
| nemotron-3-super | case-14 | 2 | 0 | 0 | 2 | 2 | [evidence](grades/133c11182e54ffed.json) |
| nemotron-3-super | case-15 | 2 | 0 | 1 | 3 | 1 | [evidence](grades/42e529dcd69dc3a0.json) |
| nemotron-3-super | case-16 | 2 | 1 | 0 | 3 | 1 | [evidence](grades/15646d04351cce25.json) |
| nemotron-3-super | case-17 | 2 | 0 | 0 | 2 | 2 | [evidence](grades/2af410eaaa5e6d45.json) |
| nemotron-3-super | case-18 | 2 | 1 | 0 | 3 | 1 | [evidence](grades/0fc9d7cf8210a474.json) |
| nemotron-3-super | case-19 | 2 | 1 | 0 | 3 | 1 | [evidence](grades/ce8af08bec081432.json) |
| nemotron-3-super | case-20 | 2 | 1 | 1 | 4 | 0 | [evidence](grades/828894dfbd1ec09f.json) |
