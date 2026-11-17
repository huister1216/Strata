# Community benchmark on AMD Radeon RX 6600 XT

Measured on 2026-11-16 with `tools/strata_bench.py` (suite 1, 3 runs per test, medians with ranges). Speeds are the engine's own timings; first-token times are measured by the client over HTTP. Speed only: no correctness check was run.

## Hardware and software

- GPU and VRAM: AMD Radeon RX 6600 XT, 8 GiB VRAM
- CPU: 12th Gen Intel(R) Core(TM) i5-12400F (6 cores, 12 threads)
- Installed RAM: 62.6 GiB
- Storage: sda     OCZ-VERTEX4            sata; zram0; nvme1n1 WDC WDBA3V5000ANC-WRSN nvme; nvme0n1 Lexar SSD NM790 1TB    nvme
- OS: Linux 7.3.3-200.fc44.x86_64
- GPU driver: the kernel's amdgpu driver, which has no version of its own;
  - CUDA (driver supports up to): not read
  - ROCm runtime: 7.13.0
- Strata: project 0.1.59.1, commit 41a195ff; engine 0.1.59.1
- Background workloads: not recorded

## Model and configuration

- Model and quantization: qwen3.8-flash-next-gyro-gyro-m
- Context: 131072 tokens; parallel slots: 1
- Settings: the install's own configuration, unchanged (hip backend); thinking off for the suite; temperature 0

```text
strata --pack gyro-gyro-m --native Qwen3.8-Flash-Next-Gyro-M-TQ2_0.gguf --ple-gguf Qwen3.8-Flash-Next-Gyro-M-TQ2_0.gguf --expert-profile expert-profile.bin --expert-cache auto --prefill auto --spec 4 --spec-min-p 0.5 --mtp rt --max-context 131072 --kv int8 --kv-resident 32768 --vision
```

Environment of the config: `STRATA_HC_PERSIST=1`, `STRATA_HIP_PROMPT_F16=1`, `STRATA_ROCBLAS_TUNING=hip`

## Method

Run by `python tools/strata_bench.py` against the HTTP API of a Strata server (started by the benchmark from the install configuration); model loading is not timed. One warm-up chat and a 1K prompt are discarded first. Every prompt starts with a unique tag, so the conversation cache cannot help the fresh-prompt tests.

- short chat: the three questions of `tools/ab_engine.py`, up to 100 new tokens, 3 runs
- 4K / 16K prompts: generated word lists sized by a calibration request, 24 new tokens, 3 fresh prompts each
- agent session: system prompt and four tools, then 5 turns that each add about 1500 words of a project file and continue from the model's own earlier answers (the way agent clients resend a conversation), 64 new tokens per turn, 3 sessions; the cache numbers come from the answer's usage (`cached_tokens`) and timings (`prompt_n`)
- concurrency (when run): N requests sent at the same moment, total tokens over the wall time of the burst, latency over all requests

## Results

| Configuration | Actual prompt tokens | Reused tokens | Generated tokens | Runs | Prompt tok/s median and range | Decode tok/s median and range | TTFT seconds median and range |
| --- | ---: | ---: | ---: | ---: | --- | --- | --- |
| short chat | 46 (43-51) | 0 | 100 (100-100) | 9 | not measured | 21.7 (19.8-31.3) | 1.56 (1.45-1.71) |
| 4K prompt, fresh | 4019 (4019-4019) | 0 (0-0) | 24 cap | 3 | 196.6 (196.5-196.6) | not measured | 20.51 (20.51-20.52) |
| 16K prompt, fresh | 16058 (16058-16058) | 0 (0-0) | 24 cap | 3 | 192.1 (189.3-193.1) | not measured | 83.65 (83.22-84.89) |
| agent session, follow-up turns | 13822 (13786-13870) at the last turn | see below | up to 64 | 3 | see below | 21.8 (19.6-26.7) | 25.46 (13.20-31.29) |

Ranges are the lowest and highest of the runs; `Runs` counts requests that returned a token.

### Agent session (conversation cache)

Cache hit over the follow-up turns: 70.1 % (70.0-70.1); earlier-turn tokens read again per session: 5 (5-5) (earlier turns that the cache did not hold; the 12990 (12989-12990) new tokens of the files are read once); first turn (nothing cached) first token: 6.54 s (6.41-6.58).

| Turn (run 1) | Prompt tokens | Reused | Read | Prompt tok/s | First token (s) | Decode tok/s |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | 609 | 0 | 609 | 96.1 | 6.407 | 23.0 |
| 1 | 4077 | 633 | 3444 | 113.3 | 30.471 | 21.7 |
| 2 | 5610 | 4140 | 1470 | 111.7 | 13.23 | 21.7 |
| 3 | 8856 | 5673 | 3183 | 102.0 | 31.289 | 21.8 |
| 4 | 11106 | 8917 | 2189 | 109.1 | 20.141 | 22.8 |
| 5 | 13870 | 11161 | 2709 | 106.7 | 25.459 | 26.7 |

Per-request data: `results.json`. Engine log lines from the start: `engine-log-excerpt.txt` (when this run started the server).

## Correctness and limitations

Not measured: this is a speed suite. The conversation uses the model's own replies, so token counts differ a little between runs. Machine details come from the server, `nvidia-smi`/`amd-smi` and the OS; background load is not recorded. Total time of the suite: 802 s.
