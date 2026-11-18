// Exact DNF model counter by enumeration, for checking count on small inputs.
// Reads the same "p dnf n m" format as count and prints
//     <satisfying assignments> <fraction of the 2^n assignments>
// Only variables that occur in some clause are enumerated, so at most 30
// distinct variables may occur; n itself may be up to 63.
//
//     g++ -O2 -o exact exact.cpp && ./exact f.dnf
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <map>
#include <sstream>
#include <string>
#include <vector>

int main(int argc, char** argv) {
    if (argc != 2) {
        std::cerr << "usage: exact file.dnf" << std::endl;
        return 2;
    }
    std::ifstream in(argv[1]);
    if (!in) {
        std::cerr << "cannot open " << argv[1] << std::endl;
        return 2;
    }
    std::string line, p, fmt;
    int n = -1, m = -1;
    while (std::getline(in, line)) {
        std::istringstream iss(line);
        if (iss >> p && p == "p") {
            iss >> fmt >> n >> m;
            break;
        }
    }
    if (n < 0 || n > 63) {
        std::cerr << "need a header with 0 <= n <= 63" << std::endl;
        return 2;
    }

    // a clause is satisfied by x iff (x & pos) == pos and (x & neg) == 0
    std::map<int, int> index;  // occurring variable -> bit
    std::vector<uint32_t> pos, neg;
    while (std::getline(in, line)) {
        std::istringstream iss(line);
        uint32_t ps = 0, ng = 0;
        int lit;
        bool any = false;
        while (iss >> lit && lit != 0) {
            any = true;
            int v = std::abs(lit);
            if (v > n) {
                std::cerr << "variable " << v << " exceeds n" << std::endl;
                return 2;
            }
            auto it = index.emplace(v, int(index.size())).first;
            if (it->second >= 30) {
                std::cerr << "more than 30 distinct variables" << std::endl;
                return 2;
            }
            if (lit > 0) ps |= 1u << it->second; else ng |= 1u << it->second;
        }
        if (!any || (ps & ng)) continue;  // contradictory clause is never satisfied
        pos.push_back(ps);
        neg.push_back(ng);
    }

    const int u = int(index.size());
    const size_t c = pos.size();
    uint64_t sat = 0;
    for (uint64_t x = 0; x < (uint64_t(1) << u); ++x) {
        uint32_t a = uint32_t(x);
        for (size_t j = 0; j < c; ++j) {
            if ((a & pos[j]) == pos[j] && (a & neg[j]) == 0) {
                ++sat;
                break;
            }
        }
    }
    printf("%llu %.17g\n", (unsigned long long)(sat << (n - u)),
           double(sat) / double(uint64_t(1) << u));
    return 0;
}
