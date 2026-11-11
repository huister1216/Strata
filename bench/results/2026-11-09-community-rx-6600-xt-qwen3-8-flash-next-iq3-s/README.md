# Community benchmark on AMD Radeon RX 6600 XT

Measured on 2026-11-09 with `tools/strata_bench.py` (suite 1, 3 runs per test, medians with ranges). Speeds are the engine's own timings; first-token times are measured by the client over HTTP. Speed only: no correctness check was run.

## Hardware and software

- GPU and VRAM: AMD Radeon RX 6600 XT, 8 GiB VRAM
- CPU: 12th Gen Intel(R) Core(TM) i5-12400F (6 cores, 12 threads)
- Installed RAM: 62.6 GiB
- Storage: sda     OCZ-VERTEX4            sata; sdb     ADATA SU635            sata; sdc     Storage Device         usb; sdd     Storage Device         usb; zram0; nvme1n1 WDC WDBA3V5000ANC-WRSN nvme; nvme0n1 Lexar SSD NM790 1TB    nvme
- OS: Linux 7.2.14-200.fc44.x86_64; Fedora Linux 44 (KDE Plasma Desktop Edition)
- GPU driver: the kernel's amdgpu driver, which has no version of its own
  - CUDA (driver supports up to): not read
  - ROCm runtime: 7.13.0
- Strata: project 0.1.58, commit 181a69f9; engine 0.1.58
- Background workloads: not recorded

## Model and configuration

- Model and quantization: qwen3.8-flash-next-iq3_s
- Context: 65536 tokens; parallel slots: 1
- Settings: the install's own configuration, unchanged (hip backend); thinking off for the suite; temperature 0

```text
strata --pack iq3_s --native Qwen3.8-Flash-Next-GSQ-RCO-IQ3_S-00001-of-00002.gguf --ple-gguf Qwen3.8-Flash-Next-GSQ-RCO-IQ3_S-00002-of-00002.gguf --expert-profile expert-profile.bin --expert-cache auto --prefill auto --spec 4 --mtp rt --max-context 65536 --kv int8 --kv-resident 32768 --vision --control-vector-scaled Qwen3.8-Flash-Next-experimental-speed-projection.gguf:1.0 --control-vector-layer-range 4 44 --cvec-mode project --cvec-dir per-layer --pcie-frac 0.35 --spec-min-p 0.70
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
| short chat | 46 (43-51) | 0 | 100 (100-100) | 9 | not measured | 21.5 (10.9-27.2) | 1.55 (1.38-2.57) |
| 4K prompt, fresh | 4019 (4019-4019) | 0 (0-0) | 24 cap | 3 | 194.4 (159.9-195.9) | not measured | 20.73 (20.57-25.19) |
| 16K prompt, fresh | 16058 (16058-16058) | 0 (0-0) | 24 cap | 3 | 196.5 (194.2-196.5) | not measured | 81.80 (81.78-82.76) |
| agent session, follow-up turns | 13602 (13588-13603) at the last turn | see below | up to 64 | 3 | see below | 22.4 (7.6-26.1) | 24.46 (12.24-29.77) |

Ranges are the lowest and highest of the runs; `Runs` counts requests that returned a token.

### Agent session (conversation cache)

Cache hit over the follow-up turns: 69.9 % (69.9-69.9); earlier-turn tokens read again per session: 5 (5-5) (earlier turns that the cache did not hold; the 12725 (12725-12726) new tokens of the files are read once); first turn (nothing cached) first token: 7.05 s (7.05-9.00).

| Turn (run 1) | Prompt tokens | Reused | Read | Prompt tok/s | First token (s) | Decode tok/s |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | 609 | 0 | 609 | 68.2 | 9.004 | 21.3 |
| 1 | 3839 | 634 | 3205 | 111.5 | 28.811 | 23.6 |
| 2 | 5372 | 3902 | 1470 | 105.8 | 13.956 | 20.6 |
| 3 | 8616 | 5435 | 3181 | 107.1 | 29.774 | 20.2 |
| 4 | 10839 | 8675 | 2164 | 106.7 | 20.35 | 26.1 |
| 5 | 13588 | 10878 | 2710 | 106.1 | 25.61 | 24.6 |

Per-request data: `results.json`. Engine log lines from the start: `engine-log-excerpt.txt` (when this run started the server).

## Correctness and limitations

Not measured: this is a speed suite. The conversation uses the model's own replies, so token counts differ a little between runs. Machine details come from the server, `nvidia-smi`/`amd-smi` and the OS; background load is not recorded. Total time of the suite: 824 s.
