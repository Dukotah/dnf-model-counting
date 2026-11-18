#!/usr/bin/env python3
"""Generate a random DNF in the format read by count.

Each clause has a width drawn uniformly from [kmin, kmax], uses distinct
variables drawn uniformly from 1..n, and negates each literal with
probability 1/2.

    python3 gen_dnf.py -n 20 -m 40 --kmin 3 --kmax 6 --seed 1 > f.dnf
"""
import argparse
import random
import sys


def random_dnf(n, m, kmin, kmax, rng):
    if not 1 <= kmin <= kmax <= min(n, 200):
        raise ValueError("need 1 <= kmin <= kmax <= min(n, 200)")
    clauses = []
    for _ in range(m):
        k = rng.randint(kmin, kmax)
        clauses.append([v if rng.random() < 0.5 else -v
                        for v in rng.sample(range(1, n + 1), k)])
    return clauses


def write_dnf(f, n, clauses):
    f.write("p dnf %d %d\n" % (n, len(clauses)))
    for c in clauses:
        f.write(" ".join(map(str, c)) + " 0\n")


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("-n", type=int, required=True, help="number of variables")
    p.add_argument("-m", type=int, required=True, help="number of clauses")
    p.add_argument("--kmin", type=int, default=3, help="minimum clause width")
    p.add_argument("--kmax", type=int, default=3, help="maximum clause width")
    p.add_argument("--seed", type=int, default=0)
    a = p.parse_args()
    rng = random.Random(a.seed)
    write_dnf(sys.stdout, a.n, random_dnf(a.n, a.m, a.kmin, a.kmax, rng))


if __name__ == "__main__":
    main()
