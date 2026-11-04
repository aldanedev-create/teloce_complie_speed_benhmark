# Teloce Compiler Benchmarks

**Stress testing and performance evaluation for the Teloce Python compiler.**

This repository contains a synthetic workload generator and benchmarking tools for evaluating Teloce's compilation performance under large projects.

The benchmark is designed to measure compilation speed, incremental rebuild performance, caching behavior, and parallel execution.

## Overview

The benchmark generates a realistic Teloce project containing `.vel` components with templates, JavaScript logic, reactive features, and scoped CSS.

### Default workload

| Metric | Value |
|---|---:|
| Source lines | 1,000,000 |
| Components | 2,000 |
| Generated source size | 37.8 MB |
| File extension | `.vel` |

Each generated component includes:

- HTML templates
- Template expressions and filters
- Conditional rendering (`v-if`, `v-else`)
- List rendering (`v-for`)
- Event handlers
- Two-way binding (`v-model`)
- JavaScript data properties
- Methods
- Computed properties
- Watchers
- Scoped CSS

This creates a substantial workload for testing different parts of the compiler.

## Getting Started

### Requirements

- Python 3.11+
- Git
- Teloce-Py
- A machine with sufficient RAM and available storage

### Installation

Clone Teloce-Py:

```bash
git clone https://github.com/aldanedev-create/teloce-py.git
cd teloce-py
pip install -e .
```

Clone or download this benchmark project separately.

Place `gen_vel.py` beside the `teloce-py` repository.

## Running Benchmarks

### 1. Generate the default workload

```bash
python gen_vel.py
```

Generates one million lines across 2,000 `.vel` files.

### 2. Generate and compile

```bash
python gen_vel.py --run
```

This generates the workload and measures:

- Cold compilation
- Unchanged rebuild
- Cache hits
- Compilation throughput

### 3. Test parallel compilation

```bash
python gen_vel.py --run --jobs auto
```

Automatically selects the available worker configuration.

You can also specify a fixed number of workers:

```bash
python gen_vel.py --run --jobs 1
python gen_vel.py --run --jobs 2
python gen_vel.py --run --jobs 4
```

### 4. Production benchmark

```bash
python gen_vel.py --run --production
```

Runs the benchmark using production settings, including minification.

### 5. Repeat measurements

```bash
python gen_vel.py --run --jobs auto --repeat 3
```

Multiple repetitions help reduce the impact of inconsistent execution times.

## Custom Workloads

The generator supports custom line counts, component counts, and output directories.

| Argument | Default | Description |
|---|---:|---|
| `--lines` | 1,000,000 | Total generated source lines |
| `--files` | 2,000 | Number of generated components |
| `--out` | `vel_stress` | Output directory |
| `--run` | Disabled | Compile and benchmark |
| `--production` | Disabled | Production build |
| `--jobs` | `auto` | Worker count |
| `--repeat` | 1 | Number of benchmark repetitions |

### Examples

Generate 100,000 lines:

```bash
python gen_vel.py --lines 100000
```

Generate 500,000 lines across 1,000 components:

```bash
python gen_vel.py --lines 500000 --files 1000
```

Generate one million lines in a single component:

```bash
python gen_vel.py --files 1 --run
```

Use a custom output directory:

```bash
python gen_vel.py --out my_benchmark
```

## Benchmark Results

The following measurements were recorded during compiler optimization work.

### Single-worker cold-build performance

| Compiler State | Build Time |
|---|---:|
| Original implementation | 549 seconds |
| After initial optimizations | 122 seconds |
| Latest optimized implementation | 109 seconds |

<details>
<summary>Performance comparison</summary>

The optimized compiler reduced the measured cold-build time from 549 seconds to 109 seconds.

- Approximately 5x faster than the original.
- Approximately 80.1% reduction in compilation time.
- An additional 10.7% reduction from 122 to 109 seconds.

</details>

### Windows stress-test results

A separate Windows benchmark reported:

| Measurement | Result |
|---|---:|
| Workload generation | 164.34 seconds |
| Cold build | 624.22 seconds |
| Unchanged rebuild | 32.10 seconds |
| Files compiled | 2,000 |
| Unchanged-build cache hits | 2,000 |

Cold and unchanged rebuild timings are separate measurements and should not be directly compared with the single-worker sandbox results.

## Compiler Optimizations

The optimization work has focused on reducing unnecessary processing throughout the compilation pipeline.

### JavaScript Tokenization

- Reuses parent-script tokens for contained blocks.
- Avoids repeated tokenization.
- Reduces intermediate allocations.
- Simplifies the lexer loop.

### Marker Lookup

- Replaces repeated full-module searches with a single-pass lookup index.
- Preserves matching behavior, including overlapping identifier prefixes.

### Template Dependencies

- Memoizes dependency extraction.
- Reduces repeated string processing.
- Avoids unnecessary prefix copying.

### Correctness

Optimization changes were checked against the original implementations using:

- 40,000 dependency-expression fuzz cases.
- Thousands of marker lookup cases.
- 3,000 randomized parent/child token-slice cases.
- Token position and EOF parity checks.

The reported test suite result was 499 passed and 2 pre-existing failures.

See [benchmark.md](benchmark.md) for the detailed measurements and methodology.

## Repository Structure

```text
.
├── gen_vel.py
├── benchmark.md
├── README.md
└── .gitignore
```

The generated `vel_stress/` directory is excluded from Git because it contains benchmark-generated files.

## Benchmarking Guidelines

For meaningful performance comparisons:

1. Use the same workload.
2. Record CPU model and available cores.
3. Record Python version and operating system.
4. Separate generation time from compilation time.
5. Measure cold builds and unchanged rebuilds independently.
6. Run multiple repetitions.
7. Compare equivalent worker configurations.
8. Verify compiler output correctness.

Benchmark results depend on hardware, storage, Python version, and system configuration.

## Purpose

This project provides a repeatable way to evaluate Teloce compiler performance as the compiler evolves.

The long-term goal is to identify performance bottlenecks, improve compilation throughput, optimize incremental builds, and maintain output correctness as Teloce grows.

---

**Project:** [Teloce-Py](https://github.com/aldanedev-create/teloce-py)

**Benchmark:** Teloce Compiler Performance Testing
