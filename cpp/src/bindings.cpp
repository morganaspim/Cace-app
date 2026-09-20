#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include "cace/runtime.hpp"
#include "cace/math/packet.hpp"
#include "cace/math/rational.hpp"
#include "cace/math/vector.hpp"
#include "cace/math/sparse_matrix.hpp"
#include "cace/math/exact_linalg.hpp"
#include "cace/math/polynomial.hpp"
#include "cace/math/affine.hpp"
#include "cace/math/geometry.hpp"
#include "cace/math/exterior.hpp"

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
    using cace::math::ExactPolynomial;
    using cace::math::ExactAffineMap;
    using cace::math::ExactSimplex;
    using cace::math::ExactExterior;
    using cace::math::ExactPlaneRotor;
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

    py::class_<ExactPolynomial>(m, "ExactPolynomial")
        .def(py::init<>())
        .def(py::init<std::size_t>())
        .def(py::init<std::size_t, std::vector<ExactPolynomial::Term>>())
        .def_property_readonly("variables", &ExactPolynomial::variables)
        .def_property_readonly("term_count", &ExactPolynomial::term_count)
        .def_property_readonly("total_degree", &ExactPolynomial::total_degree)
        .def_property_readonly("is_zero", &ExactPolynomial::is_zero)
        .def("evaluate", &ExactPolynomial::evaluate)
        .def("derivative", &ExactPolynomial::derivative)
        .def("gradient", &ExactPolynomial::gradient)
        .def("hessian", &ExactPolynomial::hessian)
        .def("scaled", &ExactPolynomial::scaled)
        .def("compose", &ExactPolynomial::compose)
        .def("canonical_text", &ExactPolynomial::canonical_text)
        .def("packet_hash", [](const ExactPolynomial& value) {
            return MathPacket::exact_polynomial(value).semantic_hash();
        })
        .def_static("constant", &ExactPolynomial::constant)
        .def_static("variable", &ExactPolynomial::variable)
        .def("__add__", [](const ExactPolynomial& a, const ExactPolynomial& b) { return a + b; }, py::is_operator())
        .def("__sub__", [](const ExactPolynomial& a, const ExactPolynomial& b) { return a - b; }, py::is_operator())
        .def("__mul__", [](const ExactPolynomial& a, const ExactPolynomial& b) { return a * b; }, py::is_operator())
        .def("__neg__", [](const ExactPolynomial& value) { return -value; }, py::is_operator())
        .def("__eq__", [](const ExactPolynomial& a, const ExactPolynomial& b) { return a == b; }, py::is_operator());

    py::class_<ExactAffineMap>(m, "ExactAffineMap")
        .def(py::init<>())
        .def(py::init<ExactMatrix, ExactVector>())
        .def_property_readonly("input_dimension", &ExactAffineMap::input_dimension)
        .def_property_readonly("output_dimension", &ExactAffineMap::output_dimension)
        .def_property_readonly("linear", &ExactAffineMap::linear,
             py::return_value_policy::reference_internal)
        .def_property_readonly("translation", &ExactAffineMap::translation,
             py::return_value_policy::reference_internal)
        .def("apply", &ExactAffineMap::apply)
        .def("compose", &ExactAffineMap::compose)
        .def("inverse", &ExactAffineMap::inverse)
        .def("jacobian_determinant", &ExactAffineMap::jacobian_determinant)
        .def("canonical_text", &ExactAffineMap::canonical_text)
        .def("packet_hash", [](const ExactAffineMap& value) {
            return MathPacket::exact_affine_map(value).semantic_hash();
        })
        .def_static("identity", &ExactAffineMap::identity)
        .def("__eq__", [](const ExactAffineMap& a, const ExactAffineMap& b) { return a == b; }, py::is_operator());

    py::class_<ExactSimplex>(m, "ExactSimplex")
        .def(py::init<std::vector<ExactVector>>())
        .def_property_readonly("dimension", &ExactSimplex::dimension)
        .def_property_readonly("vertices", &ExactSimplex::vertices,
             py::return_value_policy::reference_internal)
        .def("edge_matrix", &ExactSimplex::edge_matrix)
        .def("signed_jacobian", &ExactSimplex::signed_jacobian)
        .def("orientation", &ExactSimplex::orientation)
        .def("signed_volume", &ExactSimplex::signed_volume)
        .def("volume", &ExactSimplex::volume)
        .def("barycentric_coordinates", &ExactSimplex::barycentric_coordinates)
        .def("from_barycentric", &ExactSimplex::from_barycentric)
        .def("contains_closed", &ExactSimplex::contains_closed)
        .def("reference_map", &ExactSimplex::reference_map)
        .def("canonical_text", &ExactSimplex::canonical_text)
        .def("packet_hash", [](const ExactSimplex& value) {
            return MathPacket::exact_simplex(value).semantic_hash();
        })
        .def("__eq__", [](const ExactSimplex& a, const ExactSimplex& b) { return a == b; }, py::is_operator());

    py::class_<ExactExterior>(m, "ExactExterior")
        .def(py::init<>())
        .def(py::init<std::size_t>())
        .def(py::init<std::size_t, std::map<ExactExterior::Mask, Rational>>())
        .def_property_readonly("dimension", &ExactExterior::dimension)
        .def_property_readonly("term_count", &ExactExterior::term_count)
        .def_property_readonly("is_zero", &ExactExterior::is_zero)
        .def("coefficient", &ExactExterior::coefficient)
        .def("grade", &ExactExterior::grade)
        .def("is_homogeneous", &ExactExterior::is_homogeneous)
        .def("scaled", &ExactExterior::scaled)
        .def("wedge", &ExactExterior::wedge)
        .def("left_contraction", &ExactExterior::left_contraction)
        .def("hodge_dual", &ExactExterior::hodge_dual)
        .def("pushforward", &ExactExterior::pushforward)
        .def("canonical_text", &ExactExterior::canonical_text)
        .def("packet_hash", [](const ExactExterior& value) {
            return MathPacket::exact_exterior(value).semantic_hash();
        })
        .def_static("grade_of", &ExactExterior::grade_of)
        .def_static("scalar", &ExactExterior::scalar)
        .def_static("basis_vector", &ExactExterior::basis_vector)
        .def_static("basis_blade", &ExactExterior::basis_blade)
        .def("__add__", [](const ExactExterior& a, const ExactExterior& b) { return a + b; }, py::is_operator())
        .def("__sub__", [](const ExactExterior& a, const ExactExterior& b) { return a - b; }, py::is_operator())
        .def("__neg__", [](const ExactExterior& value) { return -value; }, py::is_operator())
        .def("__eq__", [](const ExactExterior& a, const ExactExterior& b) { return a == b; }, py::is_operator());

    py::class_<ExactPlaneRotor>(m, "ExactPlaneRotor")
        .def(py::init<std::size_t, std::size_t, std::size_t, Rational, Rational>())
        .def_property_readonly("dimension", &ExactPlaneRotor::dimension)
        .def_property_readonly("first_axis", &ExactPlaneRotor::first_axis)
        .def_property_readonly("second_axis", &ExactPlaneRotor::second_axis)
        .def_property_readonly("cosine", &ExactPlaneRotor::cosine,
             py::return_value_policy::reference_internal)
        .def_property_readonly("sine", &ExactPlaneRotor::sine,
             py::return_value_policy::reference_internal)
        .def("apply", &ExactPlaneRotor::apply)
        .def("matrix", &ExactPlaneRotor::matrix)
        .def("inverse", &ExactPlaneRotor::inverse)
        .def("compose_same_plane", &ExactPlaneRotor::compose_same_plane)
        .def("canonical_text", &ExactPlaneRotor::canonical_text)
        .def("packet_hash", [](const ExactPlaneRotor& value) {
            return MathPacket::exact_plane_rotor(value).semantic_hash();
        })
        .def("__eq__", [](const ExactPlaneRotor& a, const ExactPlaneRotor& b) { return a == b; }, py::is_operator());

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
        .def_static("from_exact_sparse_matrix", &MathPacket::exact_sparse_matrix)
        .def_static("from_exact_polynomial", &MathPacket::exact_polynomial)
        .def_static("from_exact_affine_map", &MathPacket::exact_affine_map)
        .def_static("from_exact_simplex", &MathPacket::exact_simplex)
        .def_static("from_exact_exterior", &MathPacket::exact_exterior)
        .def_static("from_exact_plane_rotor", &MathPacket::exact_plane_rotor);

    m.def("semantic_sha256", &cace::math::semantic_sha256);
}
