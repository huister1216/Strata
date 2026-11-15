# Community benchmark on AMD Radeon RX 6600 XT

Measured on 2026-11-14 with `tools/strata_bench.py` (suite 1, 3 runs per test, medians with ranges). Speeds are the engine's own timings; first-token times are measured by the client over HTTP. Speed only: no correctness check was run.

## Hardware and software

- GPU and VRAM: AMD Radeon RX 6600 XT, 8 GiB VRAM
- CPU: 12th Gen Intel(R) Core(TM) i5-12400F (6 cores, 12 threads)
- Installed RAM: 62.6 GiB
- Storage: sda     OCZ-VERTEX4            sata; zram0; nvme0n1 WDC WDBA3V5000ANC-WRSN nvme; nvme1n1 Lexar SSD NM790 1TB    nvme
- OS: Linux 7.3.3-200.fc44.x86_64
- GPU driver: the kernel's amdgpu driver, which has no version of its own;
  - CUDA (driver supports up to): not read
  - ROCm runtime: 10.1.0
- Strata: project 0.1.59.1, commit 0198d922; engine 0.1.59.1
- Background workloads: not recorded

## Model and configuration

- Model and quantization: qwen3.8-flash-next-iq3_s
- Context: 131072 tokens; parallel slots: 1
- Settings: the install's own configuration, unchanged (hip backend); thinking off for the suite; temperature 0

```text
strata --pack iq3_s --native Qwen3.8-Flash-Next-GSQ-RCO-IQ3_S-00001-of-00002.gguf --ple-gguf Qwen3.8-Flash-Next-GSQ-RCO-IQ3_S-00002-of-00002.gguf --expert-profile expert-profile.bin --expert-cache auto --prefill auto --spec 4 --spec-min-p 0.5 --mtp rt --max-context 131072 --kv int8 --kv-resident 32768 --vision
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
| short chat | 46 (43-51) | 0 | 100 (100-100) | 9 | not measured | 21.8 (20.8-28.3) | 1.47 (1.33-1.58) |
| 4K prompt, fresh | 4019 (4019-4019) | 0 (0-0) | 24 cap | 3 | 192.7 (192.6-192.8) | not measured | 20.91 (20.90-20.93) |
| 16K prompt, fresh | 16058 (16058-16058) | 0 (0-0) | 24 cap | 3 | 204.6 (203.1-204.8) | not measured | 78.55 (78.49-79.15) |
| agent session, follow-up turns | 13873 (13860-13876) at the last turn | see below | up to 64 | 3 | see below | 23.9 (21.6-26.2) | 15.66 (9.59-17.74) |

Ranges are the lowest and highest of the runs; `Runs` counts requests that returned a token.

### Agent session (conversation cache)

Cache hit over the follow-up turns: 70.1 % (70.1-70.1); earlier-turn tokens read again per session: 5 (5-5) (earlier turns that the cache did not hold; the 12991 (12991-12991) new tokens of the files are read once); first turn (nothing cached) first token: 5.38 s (5.28-5.45).

| Turn (run 1) | Prompt tokens | Reused | Read | Prompt tok/s | First token (s) | Decode tok/s |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | 609 | 0 | 609 | 116.7 | 5.281 | 17.2 |
| 1 | 4073 | 629 | 3444 | 194.8 | 17.74 | 26.1 |
| 2 | 5606 | 4136 | 1470 | 153.7 | 9.622 | 25.4 |
| 3 | 8852 | 5669 | 3183 | 183.2 | 17.443 | 22.2 |
| 4 | 11105 | 8915 | 2190 | 189.1 | 11.65 | 22.5 |
| 5 | 13873 | 11164 | 2709 | 173.8 | 15.656 | 23.4 |

Per-request data: `results.json`. Engine log lines from the start: `engine-log-excerpt.txt` (when this run started the server).

## Correctness and limitations

Not measured: this is a speed suite. The conversation uses the model's own replies, so token counts differ a little between runs. Machine details come from the server, `nvidia-smi`/`amd-smi` and the OS; background load is not recorded. Total time of the suite: 645 s.
