#!/bin/bash

#no hipBLASLt tuning table for gfx1032 with hipBLASLt 100400: the prompt's dense matrix products use plain hipBLAS (tools/hip/tune_hipblaslt makes a table: docs/AMD_HIP.md, Tuning table

cmake --build build-hip --target tune_hipblaslt
CASES=$(awk 'NR>2 {printf " --case %s,%s,%s,%s,%s", $1, $5, $2, $3, $4}' tools/hip/gfx1100-hipblaslt-100200.txt)
./build-hip/tune_hipblaslt $CASES --tuning-out tools/hip/gfx1032-hipblaslt-10400table.txt

