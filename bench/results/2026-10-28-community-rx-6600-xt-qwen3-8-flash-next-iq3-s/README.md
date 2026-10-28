# Community benchmark on AMD Radeon RX 6600 XT

Measured on 2026-10-28 with `tools/strata_bench.py` (suite 1, 3 runs per test, medians with ranges). Speeds are the engine's own timings; first-token times are measured by the client over HTTP. Speed only: no correctness check was run.

## Hardware and software

- GPU and VRAM: AMD Radeon RX 6600 XT, 8 GiB VRAM
- CPU: 12th Gen Intel(R) Core(TM) i5-12400F (6 cores, 12 threads); 
- Installed RAM: 62.6 GiB; 
- Storage: sda     OCZ-VERTEX4            sata; sdb     ADATA SU635            sata; sdc     Storage Device         usb; sdd     Storage Device         usb; zram0; nvme0n1 WDC WDBA3V5000ANC-WRSN nvme; nvme1n1 Lexar SSD NM790 1TB    nvme; 
- OS: Linux 7.2.11-200.fc44.x86_64; GPU driver: 7.2.11-200.fc44.x86_64; CUDA (driver supports up to): not read
- Strata: project 0.1.53, commit 9df02888; engine 0.1.53
- Background workloads: not recorded

## Model and configuration

- Model and quantization: qwen3.8-flash-next-iq3_s
- Context: 65536 tokens; parallel slots: 1
- Settings: the install's own configuration, unchanged (hip backend); thinking off for the suite; temperature 0

```text
strata --pack iq3_s --native Qwen3.8-Flash-Next-GSQ-RCO-IQ3_S-00001-of-00002.gguf --ple-gguf Qwen3.8-Flash-Next-GSQ-RCO-IQ3_S-00002-of-00002.gguf --expert-profile expert-profile.bin --expert-cache auto --prefill auto --spec 4 --mtp rt --max-context 65536 --kv int8 --vision --control-vector-scaled Qwen3.8-Flash-Next-experimental-speed-projection.gguf:1.0 --control-vector-layer-range 4 44 --cvec-mode project --cvec-dir per-layer --pcie-frac 0.35 --spec-min-p 0.70
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
| short chat | 46 (43-51) | 0 | 100 (100-100) | 9 | not measured | 22.1 (21.8-27.0) | 1.54 (1.39-2.02) |
| 4K prompt, fresh | 4019 (4019-4019) | 0 (0-0) | 24 cap | 3 | 198.4 (197.0-198.8) | not measured | 20.32 (20.27-20.46) |
| 16K prompt, fresh | 16058 (16058-16058) | 0 (0-0) | 24 cap | 3 | 197.6 (196.2-197.9) | not measured | 81.34 (81.19-81.91) |
| agent session, follow-up turns | 12935 (12906-12937) at the last turn | see below | up to 64 | 3 | see below | 21.2 (3.1-24.5) | 24.22 (12.25-29.73) |

Ranges are the lowest and highest of the runs; `Runs` counts requests that returned a token.

### Agent session (conversation cache)

Cache hit over the follow-up turns: 69.5 % (69.2-69.5); earlier-turn tokens read again per session: 4 (2-73) (earlier turns that the cache did not hold; the 12064 (12062-12065) new tokens of the files are read once); first turn (nothing cached) first token: 7.59 s (7.16-8.47).

| Turn (run 1) | Prompt tokens | Reused | Read | Prompt tok/s | First token (s) | Decode tok/s |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | 609 | 0 | 609 | 72.4 | 8.469 | 5.2 |
| 1 | 3355 | 626 | 2729 | 106.5 | 25.685 | 12.6 |
| 2 | 4888 | 3418 | 1470 | 105.9 | 13.94 | 11.1 |
| 3 | 8132 | 4951 | 3181 | 107.3 | 29.727 | 21.4 |
| 4 | 10201 | 8195 | 2006 | 72.6 | 27.691 | 22.1 |
| 5 | 12937 | 10254 | 2683 | 105.8 | 25.419 | 4.3 |

Per-request data: `results.json`. Engine log lines from the start: `engine-log-excerpt.txt` (when this run started the server).

## Correctness and limitations

Not measured: this is a speed suite. The conversation uses the model's own replies, so token counts differ a little between runs. Machine details come from the server, `nvidia-smi`/`rocm-smi` and the OS; background load is not recorded. Total time of the suite: 836 s.
