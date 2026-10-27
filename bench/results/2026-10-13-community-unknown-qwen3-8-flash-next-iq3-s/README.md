# Community benchmark on AMD Radeon

Measured on 2026-10-13 with `tools/strata_bench.py` (suite 1, 3 runs per test, medians with ranges). Speeds are the engine's own timings; first-token times are measured by the client over HTTP. Speed only: no correctness check was run.

## Hardware and software

- GPU and VRAM: AMD Radeon, 8 GiB VRAM
- CPU: 12th Gen Intel(R) Core(TM) i5-12400F (6 cores, 12 threads); installed RAM: 62.6 GiB; storage: not measured
- OS: Linux 7.2.9-201.fc44.x86_64; GPU driver: 7.2.9-201.fc44.x86_64; CUDA: not read
- Strata: project 0.1.43.1, commit a0116b27; engine 0.1.43.1
- Background workloads and power limits: not recorded

## Model and configuration

- Model and quantization: qwen3.8-flash-next-iq3_s
- Context: 65536 tokens; parallel slots: 1
- Settings: the install's own configuration, unchanged (hip backend); thinking off for the suite; temperature 0

```text
strata --pack iq3_s --native Qwen3.8-Flash-Next-GSQ-RCO-IQ3_S-00001-of-00002.gguf --ple-gguf Qwen3.8-Flash-Next-GSQ-RCO-IQ3_S-00002-of-00002.gguf --expert-profile expert-profile.bin --expert-cache auto --prefill auto --spec 4 --spec-min-p 0.5 --mtp rt --max-context 65536 --kv int8 --vision --vram-reserve-mib 700
```

## Method

Run by `python tools/strata_bench.py` against the HTTP API of a Strata server (started by the benchmark from the install configuration); model loading is not timed. One warm-up chat and a 1K prompt are discarded first. Every prompt starts with a unique tag, so the conversation cache cannot help the fresh-prompt tests.

- short chat: the three questions of `tools/ab_engine.py`, up to 100 new tokens, 3 runs
- 4K / 16K prompts: generated word lists sized by a calibration request, 24 new tokens, 3 fresh prompts each
- agent session: system prompt and four tools, then 5 turns that each add about 1500 words of a project file and continue from the model's own earlier answers (the way agent clients resend a conversation), 64 new tokens per turn, 3 sessions; the cache numbers come from the answer's usage (`cached_tokens`) and timings (`prompt_n`)
- concurrency (when run): N requests sent at the same moment, total tokens over the wall time of the burst, latency over all requests

## Results

| Configuration | Actual prompt tokens | Reused tokens | Generated tokens | Runs | Prompt tok/s median and range | Decode tok/s median and range | TTFT seconds median and range |
| --- | ---: | ---: | ---: | ---: | --- | --- | --- |
| short chat | 46 (43-51) | 0 | 100 (100-100) | 9 | not measured | 19.9 (14.7-26.7) | 1.52 (1.31-1.76) |
| 4K prompt, fresh | 4019 (4019-4019) | 0 (0-0) | 24 cap | 3 | 122.5 (121.6-122.5) | not measured | 32.88 (32.87-33.10) |
| 16K prompt, fresh | 16058 (16058-16058) | 0 (0-0) | 24 cap | 3 | 122.0 (120.1-122.4) | not measured | 131.67 (131.25-133.78) |
| agent session, follow-up turns | 14445 (14444-14458) at the last turn | see below | up to 64 | 3 | see below | 20.3 (14.9-25.4) | 34.75 (16.97-41.88) |

Ranges are the lowest and highest of the runs; `Runs` counts requests that returned a token.

### Agent session (conversation cache)

Cache hit over the follow-up turns: 68.8 % (68.6-68.8); earlier-turn tokens read again per session: 3 (3-74) (earlier turns that the cache did not hold; the 13634 (13633-13635) new tokens of the files are read once); first turn (nothing cached) first token: 8.89 s (8.69-10.17).

| Turn (run 1) | Prompt tokens | Reused | Read | Prompt tok/s | First token (s) | Decode tok/s |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | 609 | 0 | 609 | 60.3 | 10.167 | 20.2 |
| 1 | 3714 | 631 | 3083 | 73.7 | 41.879 | 21.7 |
| 2 | 5247 | 3778 | 1469 | 79.1 | 18.629 | 18.5 |
| 3 | 8691 | 5311 | 3380 | 81.8 | 41.405 | 20.3 |
| 4 | 11573 | 8713 | 2860 | 82.5 | 34.747 | 24.0 |
| 5 | 14444 | 11598 | 2846 | 81.2 | 35.109 | 14.9 |

Per-request data: `results.json`. Engine log lines from the start: `engine-log-excerpt.txt` (when this run started the server).

## Correctness and limitations

Not measured: this is a speed suite. The conversation uses the model's own replies, so token counts differ a little between runs. Machine details come from the server, `nvidia-smi`/`rocm-smi` and the OS; background load and power limits are not recorded. Total time of the suite: 1154 s.
