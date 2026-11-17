# Community benchmark on AMD Radeon RX 6600 XT

Measured on 2026-11-15 with `tools/strata_bench.py` (suite 1, 3 runs per test, medians with ranges). Speeds are the engine's own timings; first-token times are measured by the client over HTTP. Speed only: no correctness check was run.

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

- Model and quantization: qwen3.8-flash-next-iq3_s
- Context: 65536 tokens; parallel slots: 1
- Settings: the install's own configuration, unchanged (hip backend); thinking off for the suite; temperature 0

```text
strata --pack iq3_s --native Qwen3.8-Flash-Next-GSQ-RCO-IQ3_S-00001-of-00002.gguf --ple-gguf Qwen3.8-Flash-Next-GSQ-RCO-IQ3_S-00002-of-00002.gguf --expert-profile expert-profile.bin --expert-cache auto --prefill auto --spec 4 --mtp rt --max-context 65536 --kv int8 --kv-resident 32768 --vision --pcie-frac 0.35 --spec-min-p 0.70
```

Environment of the config: `STRATA_ADAPT_OVERLAP=1`, `STRATA_SPEC_COUPLED=1`, `STRATA_RAM_ADAPT=1`, `STRATA_HC_PERSIST=1`, `STRATA_HIP_PROMPT_F16=1`, `STRATA_MTP_HIP_PRIO=1`, `STRATA_VERIFY_COHERENT=1`, `STRATA_DOORBELL_STORE=1`, `STRATA_ROCBLAS_TUNING=hip`

## Method

Run by `python tools/strata_bench.py` against the HTTP API of a Strata server (started by the benchmark from the install configuration); model loading is not timed. One warm-up chat and a 1K prompt are discarded first. Every prompt starts with a unique tag, so the conversation cache cannot help the fresh-prompt tests.

- short chat: the three questions of `tools/ab_engine.py`, up to 100 new tokens, 3 runs
- 4K / 16K prompts: generated word lists sized by a calibration request, 24 new tokens, 3 fresh prompts each
- agent session: system prompt and four tools, then 5 turns that each add about 1500 words of a project file and continue from the model's own earlier answers (the way agent clients resend a conversation), 64 new tokens per turn, 3 sessions; the cache numbers come from the answer's usage (`cached_tokens`) and timings (`prompt_n`)
- concurrency (when run): N requests sent at the same moment, total tokens over the wall time of the burst, latency over all requests

## Results

| Configuration | Actual prompt tokens | Reused tokens | Generated tokens | Runs | Prompt tok/s median and range | Decode tok/s median and range | TTFT seconds median and range |
| --- | ---: | ---: | ---: | ---: | --- | --- | --- |
| short chat | 46 (43-51) | 0 | 100 (100-100) | 9 | not measured | 24.5 (23.1-33.3) | 1.42 (1.31-1.56) |
| 4K prompt, fresh | 4019 (4019-4019) | 0 (0-0) | 24 cap | 3 | 238.6 (237.8-239.3) | not measured | 16.90 (16.85-16.96) |
| 16K prompt, fresh | 16058 (16058-16058) | 0 (0-0) | 24 cap | 3 | 256.5 (256.2-256.9) | not measured | 62.68 (62.56-62.74) |
| agent session, follow-up turns | 13856 (13837-13859) at the last turn | see below | up to 64 | 3 | see below | 24.6 (21.7-27.3) | 18.76 (9.45-23.00) |

Ranges are the lowest and highest of the runs; `Runs` counts requests that returned a token.

### Agent session (conversation cache)

Cache hit over the follow-up turns: 70.1 % (70.1-70.1); earlier-turn tokens read again per session: 5 (5-5) (earlier turns that the cache did not hold; the 12990 (12990-12991) new tokens of the files are read once); first turn (nothing cached) first token: 5.38 s (5.25-5.41).

| Turn (run 1) | Prompt tokens | Reused | Read | Prompt tok/s | First token (s) | Decode tok/s |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | 609 | 0 | 609 | 117.4 | 5.249 | 19.4 |
| 1 | 4076 | 632 | 3444 | 150.4 | 22.956 | 23.2 |
| 2 | 5609 | 4139 | 1470 | 156.5 | 9.454 | 22.4 |
| 3 | 8855 | 5672 | 3183 | 144.3 | 22.119 | 22.3 |
| 4 | 11103 | 8914 | 2189 | 155.3 | 14.158 | 25.2 |
| 5 | 13859 | 11150 | 2709 | 144.9 | 18.755 | 27.3 |

Per-request data: `results.json`. Engine log lines from the start: `engine-log-excerpt.txt` (when this run started the server).

## Correctness and limitations

Not measured: this is a speed suite. The conversation uses the model's own replies, so token counts differ a little between runs. Machine details come from the server, `nvidia-smi`/`amd-smi` and the OS; background load is not recorded. Total time of the suite: 625 s.
