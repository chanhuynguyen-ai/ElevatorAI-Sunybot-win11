#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <cmath>
#include <string>
#include <vector>

namespace py = pybind11;

static double cosine(const std::vector<float>& a, const std::vector<float>& b) {
    if (a.empty() || b.empty() || a.size() != b.size()) return 0.0;

    double dot = 0.0, na = 0.0, nb = 0.0;
    for (size_t i = 0; i < a.size(); i++) {
        dot += (double)a[i] * (double)b[i];
        na  += (double)a[i] * (double)a[i];
        nb  += (double)b[i] * (double)b[i];
    }
    if (na == 0.0 || nb == 0.0) return 0.0;
    return dot / (std::sqrt(na) * std::sqrt(nb));
}

// Trả về (best_index, best_score)
// best_index = -1 nếu không match
static py::tuple match_index(
    const std::string& user_norm,
    const std::vector<float>& user_emb,
    const std::vector<std::string>& items_prompt_norm,
    const std::vector<std::vector<float>>& items_emb,
    double threshold
) {
    // 1) Match exact theo text normalized (nhanh nhất)
    for (size_t i = 0; i < items_prompt_norm.size(); i++) {
        if (items_prompt_norm[i] == user_norm) {
            return py::make_tuple((int)i, 1.0);
        }
    }

    // 2) Match embedding cosine best
    int best_i = -1;
    double best_s = -1.0;

    for (size_t i = 0; i < items_emb.size(); i++) {
        if (items_emb[i].empty()) continue;
        double s = cosine(user_emb, items_emb[i]);
        if (s > best_s) {
            best_s = s;
            best_i = (int)i;
        }
    }

    if (best_i >= 0 && best_s >= threshold) {
        return py::make_tuple(best_i, best_s);
    }
    return py::make_tuple(-1, 0.0);
}

PYBIND11_MODULE(sunycore_native, m) {
    m.doc() = "Sunybot native core (pybind11): cosine + semantic match";
    m.def("match_index", &match_index,
          py::arg("user_norm"),
          py::arg("user_emb"),
          py::arg("items_prompt_norm"),
          py::arg("items_emb"),
          py::arg("threshold") = 0.78
    );
}

