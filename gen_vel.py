#!/usr/bin/env python3
"""
gen_vel.py - generate N lines of .vel code to stress-test teloce-py's compiler.

Examples
--------
  # 1,000,000 lines spread over 2,000 components (realistic project), generate only
  python gen_vel.py

  # generate AND time a compile with teloce-py (cold + unchanged/cached rebuild)
  python gen_vel.py --run

  # one single giant 1,000,000-line component (worst-case parser stress)
  python gen_vel.py --files 1 --run

  # production-style build with minify
  python gen_vel.py --run --production

The output layout is a normal teloce project:
  <out>/static/js/Comp00000.vel ... + App.vel (imports nothing, so each file
  compiles independently).
The total line count across all .vel files is EXACTLY --lines.
"""
import argparse
import shutil
import statistics
import sys
import time
from pathlib import Path


# --------------------------------------------------------------------------
# One "block" = a repeatable unit of template + script + style. Every piece
# uses real .vel features: v-if/v-else, v-for, :key, @click, v-model,
# filters, computed, methods, watch, scoped CSS.
# --------------------------------------------------------------------------

def tpl_block(i):
    return [
        f'    <section class="card c{i}" :class="{{ active: active{i} }}">',
        f'      <h2>{{{{ title{i} | upper }}}}</h2>',
        f'      <p v-if="count{i} > 0">Count: {{{{ count{i} }}}}</p>',
        f'      <p v-else>Nothing yet</p>',
        f'      <ul>',
        f'        <li v-for="(item, idx) in items{i}" :key="item.id">{{{{ idx }}}}: {{{{ item.name }}}} - {{{{ item.price | currency }}}}</li>',
        f'      </ul>',
        f'      <input v-model="text{i}" placeholder="Type {i}">',
        f'      <button @click="inc{i}">+1</button> <button @click="toggle{i}">Toggle</button>',
        f'      <span>{{{{ summary{i} }}}}</span>',
        f'    </section>',
    ]  # 11 lines


def data_block(i):
    return [
        f'      title{i}: "block {i}",',
        f'      count{i}: {i % 7},',
        f'      active{i}: {"true" if i % 2 == 0 else "false"},',
        f'      text{i}: "",',
        f'      items{i}: [{{ id: 1, name: "a{i}", price: {i % 50} }}, {{ id: 2, name: "b{i}", price: {(i * 3) % 90} }}],',
    ]  # 5 lines


def method_block(i):
    return [
        f'    inc{i}() {{',
        f'      this.count{i} += 1;',
        f'    }},',
        f'    toggle{i}() {{',
        f'      this.active{i} = !this.active{i};',
        f'    }},',
    ]  # 6 lines


def computed_block(i):
    return [
        f'    summary{i}() {{',
        f'      return this.title{i} + " (" + this.count{i} + ") " + this.items{i}.length;',
        f'    }},',
    ]  # 3 lines


def watch_block(i):
    return [
        f'    text{i}(value) {{',
        f'      if (value.length > 20) {{ this.text{i} = value.slice(0, 20); }}',
        f'    }},',
    ]  # 3 lines


def style_block(i):
    return [
        f'.c{i} {{ display: block; padding: {4 + i % 12}px; margin: 2px 0; }}',
        f'.c{i}.active {{ border-left: 3px solid #{(i * 2654435) % 0xFFFFFF:06x}; }}',
        f'.c{i} h2 {{ font-size: {12 + i % 8}px; color: #333; }}',
        f'.c{i} li:hover {{ background: #f4f4f4; }}',
    ]  # 4 lines


# fixed overhead lines per component (everything that is not a repeated block)
#   template: <template>, <div class="root">, </div>, </template>      = 4
#   script  : <script>, export default {, props, data() {, return {,
#             }; }, ... see build_component for the exact skeleton
def build_component(name, target_lines, base_index):
    """Return a list of exactly `target_lines` lines for one .vel component."""
    per_block = 11 + 5 + 6 + 3 + 3 + 4  # 32 lines per block

    head_tpl = ['<template>', f'  <div class="root {name}">', f'    <h1>{name}</h1>']
    tail_tpl = ['  </div>', '</template>', '']
    script_open = [
        '<script>',
        'export default {',
        f'  name: "{name}",',
        '  props: { label: { type: String, default: "x" } },',
        '  filters: {',
        '    upper(v) { return String(v).toUpperCase(); },',
        '    currency(v) { return "$" + v; },',
        '  },',
        '  data() {',
        '    return {',
    ]
    data_close = ['    };', '  },', '  methods: {']
    methods_close = ['  },', '  computed: {']
    computed_close = ['  },', '  watch: {']
    watch_close = ['  },', '};', '</script>', '']
    style_open = ['<style scoped>', f'.{name} {{ display: block; }}']
    style_close = ['</style>']

    fixed = (len(head_tpl) + len(tail_tpl) + len(script_open) + len(data_close)
             + len(methods_close) + len(computed_close) + len(watch_close)
             + len(style_open) + len(style_close))

    blocks = max(0, (target_lines - fixed) // per_block)
    pad = target_lines - fixed - blocks * per_block  # 0..31 filler lines

    tpl, data, meth, comp, watch, style = [], [], [], [], [], []
    for b in range(blocks):
        i = base_index + b
        tpl += tpl_block(i)
        data += data_block(i)
        meth += method_block(i)
        comp += computed_block(i)
        watch += watch_block(i)
        style += style_block(i)
    # exact-count padding: harmless CSS comments inside <style>
    style += [f'/* pad {k} */' for k in range(pad)]

    lines = (head_tpl + tpl + tail_tpl + script_open + data + data_close + meth
             + methods_close + comp + computed_close + watch + watch_close
             + style_open + style + style_close)
    # Only fails if target_lines is too small for the skeleton
    if len(lines) != target_lines:
        raise ValueError(f"component needs at least {fixed} lines, got target {target_lines}")
    return lines


def generate(out_root: Path, total_lines: int, files: int):
    js_dir = out_root / "static" / "js"
    if out_root.exists():
        shutil.rmtree(out_root)
    js_dir.mkdir(parents=True)

    base, extra = divmod(total_lines, files)
    written = 0
    block_counter = 0
    t0 = time.perf_counter()
    for n in range(files):
        target = base + (1 if n < extra else 0)
        name = "App" if n == 0 else f"Comp{n:05d}"
        lines = build_component(name, target, block_counter)
        block_counter += max(0, (target - 40) // 32)
        (js_dir / f"{name}.vel").write_text("\n".join(lines) + "\n", encoding="utf-8")
        written += len(lines)
    gen_time = time.perf_counter() - t0
    return written, gen_time


def count_lines(root: Path):
    total = 0
    for p in root.rglob("*.vel"):
        with open(p, "rb") as f:
            total += sum(1 for _ in f)
    return total


def compile_benchmark(root: Path, production: bool, repeat: int, jobs="auto"):
    try:
        from teloce.build.builder import Builder
    except ImportError:
        sys.exit("teloce-py is not installed. Run: pip install teloce-py  (or pip install -e <clone>)")

    results = {}
    out_dir = root / "dist"
    opts = {
        "dev": not production,
        "production": production,
        "minify": production,
        "static_dir": "static",
        "direct_dom_updates": True,
        "clean": False,
        "jobs": jobs,
    }
    for run in range(repeat):
        if out_dir.exists():
            shutil.rmtree(out_dir)
        with Builder(dict(opts)) as builder:
            for scenario in ("cold", "unchanged"):
                t = time.perf_counter()
                res = builder.build(root, out_dir)
                dt = time.perf_counter() - t
                results.setdefault(scenario, []).append(dt)
                failed = res.get("failed")
                if failed:
                    print(f"\n!! {failed} component(s) failed. First errors:")
                    for e in res.get("errors", [])[:5]:
                        print("  ", e.get("file"), "->", e.get("error"))
                    sys.exit(1)
                print(f"  run {run + 1}/{repeat} {scenario:<9} {dt:8.2f}s  "
                      f"compiled={res.get('compiled')} cache_hits={res.get('cache_hits')}")
    return results


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--lines", type=int, default=1_000_000, help="total .vel lines (default 1,000,000)")
    ap.add_argument("--files", type=int, default=2000, help="number of .vel components (default 2000; 1 = single giant file)")
    ap.add_argument("--out", default="vel_stress", help="output project dir (default ./vel_stress)")
    ap.add_argument("--run", action="store_true", help="compile with teloce-py and report timing")
    ap.add_argument("--production", action="store_true", help="production/minified build instead of dev")
    ap.add_argument("--jobs", default="auto", help="worker processes: N, or auto = all cores (default auto)")
    ap.add_argument("--repeat", type=int, default=1, help="compile repetitions (default 1)")
    args = ap.parse_args()

    out = Path(args.out).resolve()
    print(f"Generating {args.lines:,} lines across {args.files:,} file(s) in {out} ...")
    written, gen_time = generate(out, args.lines, args.files)
    actual = count_lines(out)
    size_mb = sum(p.stat().st_size for p in out.rglob("*.vel")) / 1e6
    print(f"Done in {gen_time:.2f}s: {actual:,} lines, {size_mb:.1f} MB on disk")
    assert actual == args.lines, f"line mismatch: {actual} != {args.lines}"

    if args.run:
        print(f"\nCompiling with teloce-py ({'production' if args.production else 'dev'}, jobs={args.jobs}) ...")
        jobs = args.jobs if args.jobs == "auto" else int(args.jobs)
        res = compile_benchmark(out, args.production, args.repeat, jobs)
        cold = statistics.median(res["cold"])
        warm = statistics.median(res["unchanged"])
        print("\n=== Results (median) ===")
        print(f"cold build      : {cold:8.2f}s   ({actual / cold:,.0f} lines/sec)")
        print(f"unchanged build : {warm:8.2f}s   (cache)")


if __name__ == "__main__":
    main()
