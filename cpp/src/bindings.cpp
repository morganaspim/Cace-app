#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include "cace/runtime.hpp"
namespace py = pybind11;
PYBIND11_MODULE(_cace_runtime, m) {
    m.doc() = "CACE native runtime v0.12";
    m.def("dot", &cace::dot);
    m.def("csr_matvec", &cace::csr_matvec);
    m.def("csr_residual", &cace::csr_residual);
    m.def("csr_residual_inf", &cace::csr_residual_inf);
    m.def("dorfler_mark", &cace::dorfler_mark);
}
