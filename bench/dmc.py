"""Thin subprocess wrapper around the count executable.

    from dmc import estimate
    p = estimate([[1, -4], [1, 2, 3], [2, -4, 10], [3, 10]], n=12, eps=0.05)
    # p is an (eps, delta) estimate of the fraction of the 2^n assignments
    # that satisfy the DNF; multiply by 2**n for the model count.

The executable is looked up in $DMC_COUNT, then ../count relative to this file.
"""
import os
import subprocess
import tempfile

_HERE = os.path.dirname(os.path.abspath(__file__))
COUNT = os.environ.get("DMC_COUNT", os.path.join(_HERE, os.pardir, "count"))


def write_dnf(path, clauses, n=None):
    """Write clauses (lists of nonzero ints) to path in the input format of count."""
    if n is None:
        n = max(abs(l) for c in clauses for l in c)
    with open(path, "w") as f:
        f.write("p dnf %d %d\n" % (n, len(clauses)))
        for c in clauses:
            if not c or len(c) > 200 or 0 in c:
                raise ValueError("clauses must have 1..200 nonzero literals")
            f.write(" ".join(map(str, c)) + " 0\n")


def estimate_file(path, eps=0.05, delta=0.05, seed=None, timeout=None):
    """Run count on a .dnf file and return the estimated satisfying fraction."""
    args = [COUNT, path, repr(float(eps)), repr(float(delta))]
    if seed is not None:
        args.append(str(int(seed)))
    out = subprocess.run(args, capture_output=True, text=True, check=True,
                         timeout=timeout)
    return float(out.stdout.split()[0])


def estimate(clauses, n=None, eps=0.05, delta=0.05, seed=None, timeout=None):
    """Estimate the satisfying fraction of a DNF given as a list of clauses."""
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "f.dnf")
        write_dnf(path, clauses, n)
        return estimate_file(path, eps, delta, seed, timeout)
