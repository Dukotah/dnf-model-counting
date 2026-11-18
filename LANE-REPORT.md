# LANE 3 report: dnf-model-counting

## 1. Upstream contribution rules

- No CONTRIBUTING.md, no CI, no Makefile, no issue/PR templates. One commit ("Add files", 2026-09-15), 0 issues, 0 PRs.
- `License/` ships GNU-GPLv3.txt, GNU-LGPLv3.txt and LICENSE-MIT.txt ("Copyright (c) [2026] [National Security
  Agency]") with no statement anywhere (README, headers, sources) of which license applies to which file. Not
  guessed; the owner may want to ask in the issue.
- Authors (README): Paul Burkhardt and Kevin T. Schmitt (NSA Research Directorate), David G. Harris (UMD).

## 2. What changed and why

### `fix/build` (upstream PR candidate, one commit `96a051c`, based on `upstream/main`)

- **Header names.** `count.cpp` and `counthelp.cpp` include `<DMCrand.h>`; `count.cpp` includes `<DMChelp.h>`;
  `include/counthelp.h` includes `<DMCrand.h>`. The repo ships `include/rand.h` and `include/counthelp.h`. I renamed
  the two headers (`git mv`, 100% similarity) instead of editing the four `#include` lines. Both are tiny, but the
  rename is clearly the less invasive one: it changes zero lines of source, and the headers' own include guards
  (`DMCrand_H`, `DMChelp_H`) show `DMCrand.h`/`DMChelp.h` are the authors' original names, so the published tree
  then matches what the code (and presumably the authors' internal tree) expects. Editing includes would instead
  make the published tree diverge from their internal one. (This deviates from the brief's stated preference; the
  alternative is a 4-line diff in 3 files if the maintainers prefer it.)
- **Link order.** README and the trailing comment in `count.cpp` put `-lgmp` before the sources; with Ubuntu's
  default `--as-needed` linking this yields 27 `undefined reference to __gmpf_*` errors. Moved `-lgmp` last.
- **Makefile** (`all`, `test`, `clean`; `-O2 -std=c++17`; `-lgmp` after sources; `CXX` overridable).
- **`make test`.** The binary hardcodes `test.dnf`, eps=delta=0.05, and is randomized (`random_device` +
  `time(0)`). Note the README's 0.501296 is for the README's 12-variable example (exact value exactly 1/2), not
  for the shipped `test.dnf`. I computed `test.dnf` exactly two ways: inclusion-exclusion over its 19 clauses gives
  43675/2^20 = 0.0416517...; the brute-force counter on branch B gives 178892800 / 2^32, the same value. `make test`
  runs `count` 5 times and requires the median to be within relative error eps of that value. By the algorithm's
  guarantee each run misses with probability <= 0.05, so a spurious failure needs 3 of 5 misses (~0.1%).
- **CI** `.github/workflows/build.yml`: ubuntu-latest, matrix g++/clang++, `make` then `make test`.

### `lane/benchmark` (fork extension, off `fix/build`, commits `58ddd00` + this report)

- `count` gets optional args `count [file.dnf [eps [delta [seed]]]]`; defaults unchanged. Seed makes runs
  reproducible (it also seeds `srand48`; upstream never seeds `drand48`, which drives the clause-order shuffle).
  Missing input file / out-of-range eps,delta now exit 2 instead of reading an uninitialised header.
- `bench/gen_dnf.py` (seeded random DNF), `bench/exact.cpp` (exact enumeration over occurring variables, <=30),
  `bench/dmc.py` (subprocess wrapper: `estimate(clauses, n, eps, delta, seed)`), `bench/run_bench.py`
  (`accuracy` / `scaling` / `report`), `bench/BENCHMARK.md` with measured tables and `results/` CSVs + plot.
- `make bench` builds `count` and `bench/exact`.

## 3. Evidence

README command on `upstream/main` (WSL Ubuntu, g++ 15.2.0):
```
$ g++ -lgmp -I include/ -O3 -o count count.cpp rand.cpp counthelp.cpp
count.cpp:1:10: fatal error: DMCrand.h: No such file or directory
    1 | #include <DMCrand.h>
compilation terminated.
counthelp.cpp:3:10: fatal error: DMCrand.h: No such file or directory
compilation terminated.
```
Same command with the headers present (link-order bug alone):
```
/usr/bin/x86_64-linux-gnu-ld.bfd: /tmp/ccLbTo15.o: in function `main':
count.cpp:(.text.startup+0x56): undefined reference to `__gmpf_set_default_prec'
... (27 undefined references to __gmpf_*)
collect2: error: ld returned 1 exit status
```
`fix/build`, local:
```
$ make && make test
g++ -I include/ -O2 -std=c++17 -o count count.cpp rand.cpp counthelp.cpp -lgmp
median 0.0418772, exact 0.0416517257690430, relative error 0.0054 (eps 0.05)
PASS
$ CXX=clang++ make && make test          # clang 21.1.8
median 0.0416934, exact 0.0416517257690430, relative error 0.0010 (eps 0.05)
PASS
```
GitHub Actions on the fork (run 44202107199, success, both legs):
```
build (g++)     Test  median 0.0412521, exact 0.0416517257690430, relative error 0.0096 (eps 0.05)  PASS
build (clang++) Test  median 0.0416705, exact 0.0416517257690430, relative error 0.0005 (eps 0.05)  PASS
```
README example (as `test.dnf`), 5 runs: 0.497817 0.50277 0.498822 0.505283 0.503909 (exact 1/2).

`lane/benchmark` accuracy (1080 runs, 27 random instances n<=20, delta=0.05; Intel Core Ultra 7 258V, WSL2):
```
| eps   | runs | mean rel. err | p95    | max    | runs with err > eps |
| 0.4   | 216  | 0.0515        | 0.1219 | 0.1747 | 0 |
| 0.1   | 216  | 0.0155        | 0.0394 | 0.0724 | 0 |
| 0.025 | 216  | 0.0045        | 0.0120 | 0.0221 | 0 |
```
Scaling timings were taken under heavy machine load (10 lanes building) and are flagged as noisy in BENCHMARK.md.

## 4. Competing work

`gh issue list` / `gh pr list --state all` on NationalSecurityAgency/dnf-model-counting: none. Only other fork
(deniskolyakin77) has just the original commit. Nothing overlaps.

## 5. Draft upstream text

### Issue

**Title:** Does not compile as published: missing DMCrand.h / DMChelp.h, and -lgmp link order

**Body:**
````
The README build command fails on a clean checkout (Ubuntu, g++ 15.2, libgmp-dev 6.3.0):

    $ g++ -lgmp -I include/ -O3 -o count count.cpp rand.cpp counthelp.cpp
    count.cpp:1:10: fatal error: DMCrand.h: No such file or directory
    counthelp.cpp:3:10: fatal error: DMCrand.h: No such file or directory

The sources include <DMCrand.h> and <DMChelp.h>, but the repository ships include/rand.h and
include/counthelp.h (whose include guards are DMCrand_H and DMChelp_H).

With the headers renamed, the same command still fails to link on Debian/Ubuntu, because -lgmp comes
before the sources and those toolchains link with --as-needed:

    count.cpp:(.text.startup+0x56): undefined reference to `__gmpf_set_default_prec'
    ... (27 undefined references to __gmpf_*)

Putting -lgmp after the sources fixes it:

    g++ -I include/ -O3 -o count count.cpp rand.cpp counthelp.cpp -lgmp

Separately: License/ contains GPLv3, LGPLv3 and MIT texts. Could you say which license applies?
````

### PR

**Title:** Fix build: header names, -lgmp link order; add Makefile and CI

**Body:**
````
Fixes the build as published (see issue).

- Rename include/rand.h -> include/DMCrand.h and include/counthelp.h -> include/DMChelp.h, the names the
  sources and the headers' own include guards use. No source lines change.
- Move -lgmp after the sources in the README command (and the comment at the end of count.cpp); with
  --as-needed linkers the library was dropped and linking failed.
- Add a small Makefile: `make`, `make test`, `make clean`.
- `make test` runs count on test.dnf five times and checks the median is within eps = 0.05 relative
  error of the exact satisfying fraction, 43675/2^20 = 0.0416517 (computed by inclusion-exclusion over
  the 19 clauses and confirmed by enumeration). A single run misses with probability at most delta =
  0.05, so the median check fails spuriously only if 3 of 5 runs miss (~0.1%).
- Add a GitHub Actions workflow building and testing with gcc and clang.

Tested on Ubuntu with g++ 15.2.0 and clang 21.1.8, and on ubuntu-latest in Actions.

Note: the README's example output 0.501296 is for the 12-variable example in the README (exact value
1/2), not for the shipped test.dnf, which is a different 32-variable formula.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
````

## 6. Land probability and next steps

**High on merit, unknown responsiveness.** The fix is tiny, unambiguous and required for anyone to build the
code; but this is a single-drop research release with no activity since publication, so it may never be looked at.
Owner: review `fix/build` (one commit), open the issue first, then the PR from `Dukotah:fix/build` — one push, no
follow-up nagging. If they prefer editing includes over renaming headers, that is a 4-line change.
`lane/benchmark` stays fork-only.

Note on commit trailers: LANE-RULES asks for `Co-Authored-By: Claude Fable 5.1`; these commits were written by
Claude Opus 5.5, so the trailers say that instead. Amend if the owner wants the rule's exact text.
