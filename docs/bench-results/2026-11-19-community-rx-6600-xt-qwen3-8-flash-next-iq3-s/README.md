# Community benchmark on AMD Radeon RX 6600 XT

Measured on 2026-11-19 with `tools/strata_bench.py` (suite 1, 3 runs per test, medians with ranges). Speeds are the engine's own timings; first-token times are measured by the client over HTTP. Speed only: no correctness check was run.

## Hardware and software

- GPU and VRAM: AMD Radeon RX 6600 XT, 8 GiB VRAM
- CPU: 12th Gen Intel(R) Core(TM) i5-12400F (6 cores, 12 threads)
- Installed RAM: 62.6 GiB
- Storage: sda     OCZ-VERTEX4            sata; zram0; nvme0n1 WDC WDBA3V5000ANC-WRSN nvme; nvme1n1 Lexar SSD NM790 1TB    nvme
- OS: Fedora Linux 44 (KDE Plasma Desktop Edition), Linux kernel 7.3.4-200.fc44.x86_64
- GPU driver: the kernel's amdgpu driver, which has no version of its own;
  - CUDA (driver supports up to): not read
  - ROCm runtime: 7.13.0
- Strata: project 0.1.62, commit not a git checkout; engine 0.1.62
- Background workloads: not recorded

## Model and configuration

- Model and quantization: qwen3.8-flash-next-iq3_s
- Context: 131072 tokens; parallel slots: 1
- Settings: the install's own configuration, unchanged (hip backend); thinking off for the suite; temperature 0

```text
strata --pack iq3_s --native Qwen3.8-Flash-Next-GSQ-RCO-IQ3_S-00001-of-00002.gguf --ple-gguf Qwen3.8-Flash-Next-GSQ-RCO-IQ3_S-00002-of-00002.gguf --expert-profile expert-profile.bin --expert-cache auto --prefill auto --spec 4 --spec-min-p 0.5 --mtp rt --max-context 131072 --kv int8 --kv-resident 32768 --vision
```

Environment of the config: `STRATA_ROCBLAS_TUNING=hip`, `STRATA_ARENA_THP=1`

## Method

Run by `python tools/strata_bench.py` against the HTTP API of a Strata server (started by the benchmark from the install configuration); model loading is not timed. One warm-up chat and a 1K prompt are discarded first. Every prompt starts with a unique tag, so the conversation cache cannot help the fresh-prompt tests.

- short chat: the three questions of `tools/ab_engine.py`, up to 100 new tokens, 3 runs
- 4K / 16K prompts: generated word lists sized by a calibration request, 24 new tokens, 3 fresh prompts each
- agent session: system prompt and four tools, then 5 turns that each add about 1500 words of a project file and continue from the model's own earlier answers (the way agent clients resend a conversation), 64 new tokens per turn, 3 sessions; the cache numbers come from the answer's usage (`cached_tokens`) and timings (`prompt_n`)
- concurrency (when run): N requests sent at the same moment, total tokens over the wall time of the burst, latency over all requests

## Results

| Configuration | Actual prompt tokens | Reused tokens | Generated tokens | Runs | Prompt tok/s median and range | Decode tok/s median and range | TTFT seconds median and range |
| --- | ---: | ---: | ---: | ---: | --- | --- | --- |
| short chat | 46 (43-51) | 0 | 100 (100-100) | 9 | not measured | 23.3 (21.9-31.4) | 1.41 (1.34-1.66) |
| 4K prompt, fresh | 4019 (4019-4019) | 0 (0-0) | 24 cap | 3 | 240.4 (238.8-240.7) | not measured | 16.78 (16.76-16.89) |
| 16K prompt, fresh | 16058 (16058-16058) | 0 (0-0) | 24 cap | 3 | 240.2 (231.4-240.3) | not measured | 66.93 (66.89-69.47) |
| agent session, follow-up turns | 9095 (9087-9103) at the last turn | see below | up to 64 | 3 | see below | 23.7 (20.6-28.1) | 11.07 (8.68-11.49) |

Ranges are the lowest and highest of the runs; `Runs` counts requests that returned a token.

### Agent session (conversation cache)

Cache hit over the follow-up turns: 71.1 % (71.1-71.1); earlier-turn tokens read again per session: 5 (5-5) (earlier turns that the cache did not hold; the 8209 (8209-8209) new tokens of the files are read once); first turn (nothing cached) first token: 6.62 s (6.48-6.63).

| Turn (run 1) | Prompt tokens | Reused | Read | Prompt tok/s | First token (s) | Decode tok/s |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | 609 | 0 | 609 | 95.0 | 6.482 | 17.8 |
| 1 | 2263 | 621 | 1642 | 190.5 | 8.676 | 22.6 |
| 2 | 3969 | 2326 | 1643 | 166.9 | 9.906 | 25.1 |
| 3 | 5675 | 4032 | 1643 | 149.2 | 11.075 | 28.1 |
| 4 | 7381 | 5738 | 1643 | 145.2 | 11.379 | 26.7 |
| 5 | 9087 | 7444 | 1643 | 143.8 | 11.488 | 23.7 |

Per-request data: `results.json`. Engine log lines from the start: `engine-log-excerpt.txt` (when this run started the server).

## Correctness and limitations

Not measured: this is a speed suite. The conversation uses the model's own replies, so token counts differ a little between runs. Machine details come from the server, `nvidia-smi`/`amd-smi` and the OS; background load is not recorded. Total time of the suite: 539 s.
