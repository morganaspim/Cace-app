#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include "cace/runtime.hpp"
#include "cace/math/packet.hpp"
#include "cace/math/rational.hpp"
#include "cace/math/vector.hpp"
#include "cace/math/sparse_matrix.hpp"
#include "cace/math/exact_linalg.hpp"

namespace py = pybind11;

PYBIND11_MODULE(_cace_runtime, m) {
    m.doc() = "CACE native runtime with Rigorous Math Kernel primitives";
    m.def("dot", &cace::dot);
    m.def("csr_matvec", &cace::csr_matvec);
    m.def("csr_residual", &cace::csr_residual);
    m.def("csr_residual_inf", &cace::csr_residual_inf);
    m.def("dorfler_mark", &cace::dorfler_mark);

    using cace::math::ExactVector;
    using cace::math::ExactMatrix;
    using cace::math::ExactSparseMatrix;
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

    py::class_<ExactMatrix>(m, "ExactMatrix")
        .def(py::init<>())
        .def(py::init<std::size_t, std::size_t>())
        .def(py::init<std::size_t, std::size_t, std::vector<Rational>>())
        .def_property_readonly("rows", &ExactMatrix::rows)
        .def_property_readonly("cols", &ExactMatrix::cols)
        .def("at", static_cast<const Rational& (ExactMatrix::*)(std::size_t, std::size_t) const>(&ExactMatrix::at),
             py::return_value_policy::reference_internal)
        .def("transpose", &ExactMatrix::transpose)
        .def("matvec", &ExactMatrix::matvec)
        .def("matmul", &ExactMatrix::matmul)
        .def("row_permuted", &ExactMatrix::row_permuted)
        .def("col_permuted", &ExactMatrix::col_permuted)
        .def("canonical_text", &ExactMatrix::canonical_text)
        .def("packet_hash", [](const ExactMatrix& value) {
            return MathPacket::exact_matrix(value).semantic_hash();
        })
        .def_static("identity", &ExactMatrix::identity)
        .def("__eq__", [](const ExactMatrix& a, const ExactMatrix& b) { return a == b; }, py::is_operator());

    py::class_<ExactSparseMatrix>(m, "ExactSparseMatrix")
        .def(py::init<>())
        .def_property_readonly("rows", &ExactSparseMatrix::rows)
        .def_property_readonly("cols", &ExactSparseMatrix::cols)
        .def_property_readonly("nnz", &ExactSparseMatrix::nnz)
        .def("at", &ExactSparseMatrix::at)
        .def("to_dense", &ExactSparseMatrix::to_dense)
        .def("transpose", &ExactSparseMatrix::transpose)
        .def("matvec", &ExactSparseMatrix::matvec)
        .def("matmul", &ExactSparseMatrix::matmul)
        .def("row_permuted", &ExactSparseMatrix::row_permuted)
        .def("col_permuted", &ExactSparseMatrix::col_permuted)
        .def("canonical_text", &ExactSparseMatrix::canonical_text)
        .def("packet_hash", [](const ExactSparseMatrix& value) {
            return MathPacket::exact_sparse_matrix(value).semantic_hash();
        })
        .def_static("from_dense", &ExactSparseMatrix::from_dense)
        .def_static("from_triplets", &ExactSparseMatrix::from_triplets)
        .def("__eq__", [](const ExactSparseMatrix& a, const ExactSparseMatrix& b) { return a == b; }, py::is_operator());

    m.def("exact_determinant", &cace::math::determinant);
    m.def("exact_rank", &cace::math::rank);
    m.def("exact_solve_nonsingular", &cace::math::solve_nonsingular);
    m.def("exact_inverse_nonsingular", &cace::math::inverse_nonsingular);
    m.def("exact_nullspace", &cace::math::nullspace);
    m.def("exact_verify_solution", &cace::math::verify_solution);
    m.def("exact_verify_inverse", &cace::math::verify_inverse);
    m.def("exact_is_positive_definite", &cace::math::is_positive_definite);
    m.def("exact_is_negative_definite", &cace::math::is_negative_definite);

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
        .def_static("from_exact_vector", &MathPacket::exact_vector)
        .def_static("from_exact_matrix", &MathPacket::exact_matrix)
        .def_static("from_exact_sparse_matrix", &MathPacket::exact_sparse_matrix);

    m.def("semantic_sha256", &cace::math::semantic_sha256);
}
