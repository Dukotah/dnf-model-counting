#!/usr/bin/env python3
"""Accuracy and scaling benchmark for count.

accuracy: random DNFs small enough to count exactly (bench/exact), each
          estimated repeatedly at several eps with delta fixed; reports the
          relative error |est - exact| / exact and how often it exceeds eps.
scaling:  wall time of count on larger random DNFs (no exact reference).

Writes CSVs and a plot to bench/results/. Run from the repository root after
`make bench`:

    python3 bench/run_bench.py accuracy
    python3 bench/run_bench.py scaling
    python3 bench/run_bench.py report     # re-summarise accuracy.csv
"""
import argparse
import csv
import os
import random
import statistics
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dmc import estimate_file  # noqa: E402
from gen_dnf import random_dnf, write_dnf  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
EXACT = os.path.join(HERE, "exact")
RESULTS = os.path.join(HERE, "results")


def exact_fraction(path):
    out = subprocess.run([EXACT, path], capture_output=True, text=True, check=True)
    return float(out.stdout.split()[1])


def make_instance(d, n, m, kmin, kmax, seed):
    path = os.path.join(d, "f.dnf")
    with open(path, "w") as f:
        write_dnf(f, n, random_dnf(n, m, kmin, kmax, random.Random(seed)))
    return path


def write_csv(name, rows):
    os.makedirs(RESULTS, exist_ok=True)
    with open(os.path.join(RESULTS, name), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def accuracy(args):
    epss = [0.4, 0.2, 0.1, 0.05, 0.025]
    configs = [(n, m, kmin, kmax)
               for n in (10, 16, 20)
               for (m, kmin, kmax) in ((5, 2, 4), (20, 3, 6), (80, 5, 9))]
    rows = []
    seed = 1000
    with tempfile.TemporaryDirectory() as d:
        for (n, m, kmin, kmax) in configs:
            for inst in range(args.instances):
                path = make_instance(d, n, m, kmin, kmax, 7919 * inst + n * m)
                exact = exact_fraction(path)
                for eps in epss:
                    for _ in range(args.runs):
                        seed += 1
                        t = time.perf_counter()
                        est = estimate_file(path, eps, args.delta, seed)
                        dt = time.perf_counter() - t
                        rows.append(dict(n=n, m=m, kmin=kmin, kmax=kmax, inst=inst,
                                         eps=eps, delta=args.delta, seed=seed,
                                         exact=exact, est=est,
                                         relerr=abs(est - exact) / exact,
                                         seconds=dt))
                print("n=%d m=%d k=%d..%d inst=%d exact=%.6f"
                      % (n, m, kmin, kmax, inst, exact), file=sys.stderr)
    write_csv("accuracy.csv", rows)
    report_rows(rows, args.delta)


def report(args):
    with open(os.path.join(RESULTS, "accuracy.csv")) as f:
        rows = [dict(r, eps=float(r["eps"]), relerr=float(r["relerr"]),
                     seconds=float(r["seconds"])) for r in csv.DictReader(f)]
    report_rows(rows, float(rows[0]["delta"]))


def report_rows(rows, delta):
    epss = sorted({r["eps"] for r in rows}, reverse=True)
    summary = []
    for eps in epss:
        errs = sorted(r["relerr"] for r in rows if r["eps"] == eps)
        secs = [r["seconds"] for r in rows if r["eps"] == eps]
        summary.append(dict(
            eps=eps, runs=len(errs),
            mean=statistics.fmean(errs),
            p95=errs[int(0.95 * (len(errs) - 1))],
            max=errs[-1],
            over=sum(e > eps for e in errs),
            ms=1000 * statistics.median(secs)))
    print("| eps | runs | mean rel. err | p95 rel. err | max rel. err "
          "| runs with err > eps | median ms/run |")
    print("|---:|---:|---:|---:|---:|---:|---:|")
    for s in summary:
        print("| %g | %d | %.4f | %.4f | %.4f | %d (%.2f%%) | %.1f |"
              % (s["eps"], s["runs"], s["mean"], s["p95"], s["max"],
                 s["over"], 100.0 * s["over"] / s["runs"], s["ms"]))

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import matplotlib.ticker
    except ImportError:
        print("matplotlib not installed; skipping plot", file=sys.stderr)
        return
    fig, ax = plt.subplots(figsize=(6, 4.2))
    xs = [s["eps"] for s in summary]
    ax.plot(xs, xs, "k--", lw=1, label="eps (bound, holds w.p. >= 1-delta)")
    ax.plot(xs, [s["max"] for s in summary], "o-", label="max")
    ax.plot(xs, [s["p95"] for s in summary], "s-", label="95th percentile")
    ax.plot(xs, [s["mean"] for s in summary], "^-", label="mean")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xticks(xs, [("%g" % x) for x in xs])
    ax.xaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
    ax.set_xlabel("eps")
    ax.set_ylabel("relative error vs exact count")
    ax.set_title("count, delta=%g, %d runs per eps" % (delta, summary[0]["runs"]))
    ax.legend(fontsize=8)
    ax.grid(True, which="both", alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(RESULTS, "relerr_vs_eps.png"), dpi=120)


def scaling(args):
    n = 10000
    rows = []
    with tempfile.TemporaryDirectory() as d:
        for m in (1000, 10000, 100000):
            path = make_instance(d, n, m, 15, 25, m)
            for eps in (0.1, 0.05):
                times, ests = [], []
                for r in range(args.runs):
                    t = time.perf_counter()
                    ests.append(estimate_file(path, eps, args.delta, 17 + r))
                    times.append(time.perf_counter() - t)
                rows.append(dict(n=n, m=m, eps=eps, delta=args.delta, runs=args.runs,
                                 median_s=statistics.median(times),
                                 est_mean=statistics.fmean(ests),
                                 est_stdev=statistics.stdev(ests) if len(ests) > 1 else 0.0))
                print("m=%d eps=%g median %.3fs" % (m, eps, rows[-1]["median_s"]),
                      file=sys.stderr)
    write_csv("scaling.csv", rows)
    print("| n | m | eps | median wall s (incl. parsing) | mean estimate | stdev |")
    print("|---:|---:|---:|---:|---:|---:|")
    for r in rows:
        print("| %d | %d | %g | %.3f | %.4g | %.2g |"
              % (r["n"], r["m"], r["eps"], r["median_s"], r["est_mean"], r["est_stdev"]))


def main():
    p = argparse.ArgumentParser(description="benchmark count")
    p.add_argument("what", choices=["accuracy", "scaling", "report"],
                   help="report: re-summarise results/accuracy.csv without rerunning")
    p.add_argument("--runs", type=int, default=10, help="runs per (instance, eps)")
    p.add_argument("--instances", type=int, default=3, help="instances per config (accuracy)")
    p.add_argument("--delta", type=float, default=0.05)
    args = p.parse_args()
    {"accuracy": accuracy, "scaling": scaling, "report": report}[args.what](args)


if __name__ == "__main__":
    main()
