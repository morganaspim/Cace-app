#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include "cace/runtime.hpp"
#include "cace/math/packet.hpp"
#include "cace/math/rational.hpp"
#include "cace/math/vector.hpp"

namespace py = pybind11;

PYBIND11_MODULE(_cace_runtime, m) {
    m.doc() = "CACE native runtime with Rigorous Math Kernel primitives";
    m.def("dot", &cace::dot);
    m.def("csr_matvec", &cace::csr_matvec);
    m.def("csr_residual", &cace::csr_residual);
    m.def("csr_residual_inf", &cace::csr_residual_inf);
    m.def("dorfler_mark", &cace::dorfler_mark);

    using cace::math::ExactVector;
    using cace::math::MathPacket;
    using cace::math::Rational;

    py::class_<Rational>(m, "ExactRational")
        .def(py::init<>())
        .def(py::init<Rational::rep>())
        .def(py::init<Rational::rep, Rational::rep>())
        .def_property_readonly("numerator", &Rational::numerator)
        .def_property_readonly("denominator", &Rational::denominator)
        .def_property_readonly("is_zero", &Rational::is_zero)
        .def_property_readonly("is_integer", &Rational::is_integer)
        .def("integer_exact", &Rational::integer_exact)
        .def("canonical_text", &Rational::canonical_text)
        .def("packet_hash", [](const Rational& value) {
            return MathPacket::rational(value).semantic_hash();
        })
        .def("__repr__", [](const Rational& value) {
            return "ExactRational(" + value.canonical_text() + ")";
        })
        .def("__add__", [](const Rational& a, const Rational& b) { return a + b; }, py::is_operator())
        .def("__sub__", [](const Rational& a, const Rational& b) { return a - b; }, py::is_operator())
        .def("__mul__", [](const Rational& a, const Rational& b) { return a * b; }, py::is_operator())
        .def("__truediv__", [](const Rational& a, const Rational& b) { return a / b; }, py::is_operator())
        .def("__neg__", [](const Rational& value) { return -value; }, py::is_operator())
        .def("__eq__", [](const Rational& a, const Rational& b) { return a == b; }, py::is_operator())
        .def("__lt__", [](const Rational& a, const Rational& b) { return a < b; }, py::is_operator());

    py::class_<ExactVector>(m, "ExactVector")
        .def(py::init<>())
        .def(py::init<std::vector<Rational>>())
        .def_property_readonly("size", &ExactVector::size)
        .def("at", static_cast<const Rational& (ExactVector::*)(std::size_t) const>(&ExactVector::at),
             py::return_value_policy::reference_internal)
        .def("dot", &ExactVector::dot)
        .def("squared_l2_norm", &ExactVector::squared_l2_norm)
        .def("scaled", &ExactVector::scaled)
        .def("canonical_text", &ExactVector::canonical_text)
        .def("packet_hash", [](const ExactVector& value) {
            return MathPacket::exact_vector(value).semantic_hash();
        })
        .def("__repr__", [](const ExactVector& value) {
            return "ExactVector(" + value.canonical_text() + ")";
        })
        .def("__add__", [](const ExactVector& a, const ExactVector& b) { return a + b; }, py::is_operator())
        .def("__sub__", [](const ExactVector& a, const ExactVector& b) { return a - b; }, py::is_operator())
        .def("__eq__", [](const ExactVector& a, const ExactVector& b) { return a == b; }, py::is_operator());

    py::class_<MathPacket>(m, "MathPacket")
        .def(py::init<>())
        .def_readwrite("schema_version", &MathPacket::schema_version)
        .def_readwrite("type_id", &MathPacket::type_id)
        .def_readwrite("exact_payload", &MathPacket::exact_payload)
        .def_readwrite("conventions", &MathPacket::conventions)
        .def_readwrite("source_module", &MathPacket::source_module)
        .def_readwrite("source_version", &MathPacket::source_version)
        .def_readwrite("dependency_hashes", &MathPacket::dependency_hashes)
        .def("canonical_serialize", &MathPacket::canonical_serialize)
        .def("semantic_hash", &MathPacket::semantic_hash)
        .def_static("from_rational", &MathPacket::rational)
        .def_static("from_exact_vector", &MathPacket::exact_vector);

    m.def("semantic_sha256", &cace::math::semantic_sha256);
}
