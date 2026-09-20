#include "cace/runtime.hpp"
#include "cace/exact_fem.hpp"
#include <cstdint>
#include <memory>
#include <vector>
#include <exception>
extern "C" {
int cace_csr_matvec(const double* data,const int* indices,const int* indptr,int nrows,int nnz,const double* x,int nx,double* y) {
    try { std::vector<double>d(data,data+nnz), xv(x,x+nx); std::vector<int>ix(indices,indices+nnz), ip(indptr,indptr+nrows+1); auto r=cace::csr_matvec(d,ix,ip,xv); for(int i=0;i<nrows;++i)y[i]=r[i]; return 0; } catch(...) { return -1; }
}
int cace_csr_residual_inf(const double* data,const int* indices,const int* indptr,int nrows,int nnz,const double* x,int nx,const double* b,int nb,double* out) {
    try { std::vector<double>d(data,data+nnz), xv(x,x+nx), bv(b,b+nb); std::vector<int>ix(indices,indices+nnz), ip(indptr,indptr+nrows+1); *out=cace::csr_residual_inf(d,ix,ip,xv,bv); return 0; } catch(...) { return -1; }
}
int cace_dorfler_mark(const double* eta,int n,double theta,int* out_idx,int out_cap,int* out_n) {
    try { std::vector<double>e(eta,eta+n); auto m=cace::dorfler_mark(e,theta); if((int)m.size()>out_cap)return -2; *out_n=(int)m.size(); for(int i=0;i<*out_n;++i)out_idx[i]=m[i]; return 0; } catch(...) { return -1; }
}
int cace_p1_1d_stiffness(const double* nodes,int n_nodes,double* out_data,int* out_indices,int* out_indptr,int data_cap,int* out_nnz,int* out_nrows) {
    try {
        std::vector<double> x(nodes,nodes+n_nodes), data; std::vector<int> indices, indptr;
        cace::p1_1d_reduced_stiffness(x,data,indices,indptr);
        if((int)data.size()>data_cap) return -2;
        *out_nnz=(int)data.size(); *out_nrows=(int)indptr.size()-1;
        for(int i=0;i<*out_nnz;++i){ out_data[i]=data[i]; out_indices[i]=indices[i]; }
        for(int i=0;i<=*out_nrows;++i) out_indptr[i]=indptr[i];
        return 0;
    } catch(...) { return -1; }
}
int cace_sparse_ldlt_stats(const double* data,const int* indices,const int* indptr,int nrows,int nnz,const int* order,int norder,int* out_factor_nnz,int* out_fill,double* out_min_pivot){
    try { std::vector<double>d(data,data+nnz); std::vector<int>ix(indices,indices+nnz),ip(indptr,indptr+nrows+1),ord(order,order+norder); auto r=cace::sparse_ldlt_stats(d,ix,ip,ord); if(!r.success)return -2; *out_factor_nnz=r.factor_nnz;*out_fill=r.fill_edges;*out_min_pivot=r.min_pivot;return 0;} catch(...){return -1;}
}
int cace_sparse_ldlt_solve(const double* data,const int* indices,const int* indptr,int nrows,int nnz,const int* order,int norder,const double* b,int nb,double* out_x,int out_cap,int* out_factor_nnz,int* out_fill,double* out_min_pivot){
    try { std::vector<double>d(data,data+nnz),bv(b,b+nb);std::vector<int>ix(indices,indices+nnz),ip(indptr,indptr+nrows+1),ord(order,order+norder);auto r=cace::sparse_ldlt_solve(d,ix,ip,ord,bv);if(!r.success)return -2;if((int)r.x.size()>out_cap)return -3;for(int i=0;i<(int)r.x.size();++i)out_x[i]=r.x[i];*out_factor_nnz=r.factor_nnz;*out_fill=r.fill_edges;*out_min_pivot=r.min_pivot;return 0;} catch(...){return -1;}
}

int cace_sparse_multifrontal_ldlt_solve(const double* data,const int* indices,const int* indptr,int nrows,int nnz,const int* order,int norder,const double* b,int nb,int max_parallel_depth,double* out_x,int out_cap,int* out_factor_nnz,int* out_fill,double* out_min_pivot,int* out_peak_front,long long* out_total_front_entries,int* out_parallel_tasks,double* out_ms){
    try { std::vector<double>d(data,data+nnz),bv(b,b+nb);std::vector<int>ix(indices,indices+nnz),ip(indptr,indptr+nrows+1),ord(order,order+norder);auto r=cace::sparse_multifrontal_ldlt_solve(d,ix,ip,ord,bv,max_parallel_depth);if(!r.success)return -2;if((int)r.x.size()>out_cap)return -3;for(int i=0;i<(int)r.x.size();++i)out_x[i]=r.x[i];*out_factor_nnz=r.factor_nnz;*out_fill=r.fill_edges;*out_min_pivot=r.min_pivot;*out_peak_front=r.peak_front_size;*out_total_front_entries=r.total_front_entries;*out_parallel_tasks=r.parallel_tasks;*out_ms=r.factor_solve_ms;return 0;} catch(...){return -1;}
}


int cace_sparse_supernodal_ldlt_solve(const double* data,const int* indices,const int* indptr,int nrows,int nnz,const int* order,int norder,const double* b,int nb,int threads,double* out_x,int out_cap,int* out_factor_nnz,int* out_fill,double* out_min_pivot,int* out_supernodes,int* out_max_supernode,int* out_peak_front,long long* out_total_front_entries,long long* out_block_flop_proxy,int* out_threads,int* out_tasks,int* out_workspace_reallocs,long long* out_peak_workspace_entries,double* out_ms){
    try { std::vector<double>d(data,data+nnz),bv(b,b+nb);std::vector<int>ix(indices,indices+nnz),ip(indptr,indptr+nrows+1),ord(order,order+norder);auto r=cace::sparse_supernodal_ldlt_solve(d,ix,ip,ord,bv,threads);if(!r.success)return -2;if((int)r.x.size()>out_cap)return -3;for(int i=0;i<(int)r.x.size();++i)out_x[i]=r.x[i];*out_factor_nnz=r.factor_nnz;*out_fill=r.fill_edges;*out_min_pivot=r.min_pivot;*out_supernodes=r.supernodes;*out_max_supernode=r.max_supernode_size;*out_peak_front=r.peak_front_size;*out_total_front_entries=r.total_front_entries;*out_block_flop_proxy=r.block_flop_proxy;*out_threads=r.thread_count;*out_tasks=r.scheduled_tasks;*out_workspace_reallocs=r.workspace_reallocations;*out_peak_workspace_entries=r.peak_workspace_entries;*out_ms=r.factor_solve_ms;return 0;} catch(...){return -1;}
}


struct CaceExactMeshHandle {
    cace::exact::ExactMesh mesh;
};

void* cace_exact_mesh_create(
    const std::int64_t* coordinate_numerators,
    const std::int64_t* coordinate_denominators,
    int vertex_count,
    const int* triangle_vertex_ids,
    int triangle_count) {
    try {
        if (!coordinate_numerators || !coordinate_denominators || !triangle_vertex_ids) return nullptr;
        if (vertex_count < 3 || triangle_count < 1) return nullptr;

        std::vector<cace::exact::Point2> vertices;
        vertices.reserve(static_cast<std::size_t>(vertex_count));
        for (int i = 0; i < vertex_count; ++i) {
            const std::size_t x = static_cast<std::size_t>(2 * i);
            const std::size_t y = x + 1;
            vertices.push_back({
                cace::exact::Rational(coordinate_numerators[x], coordinate_denominators[x]),
                cace::exact::Rational(coordinate_numerators[y], coordinate_denominators[y]),
            });
        }

        std::vector<std::array<std::size_t, 3>> triangles;
        triangles.reserve(static_cast<std::size_t>(triangle_count));
        for (int cell = 0; cell < triangle_count; ++cell) {
            const int a = triangle_vertex_ids[3 * cell + 0];
            const int b = triangle_vertex_ids[3 * cell + 1];
            const int d = triangle_vertex_ids[3 * cell + 2];
            if (a < 0 || b < 0 || d < 0) return nullptr;
            triangles.push_back({
                static_cast<std::size_t>(a),
                static_cast<std::size_t>(b),
                static_cast<std::size_t>(d),
            });
        }

        auto handle = std::make_unique<CaceExactMeshHandle>();
        handle->mesh = cace::exact::build_mesh(std::move(vertices), std::move(triangles));
        return handle.release();
    } catch (...) {
        return nullptr;
    }
}

void cace_exact_mesh_destroy(void* raw_handle) {
    delete static_cast<CaceExactMeshHandle*>(raw_handle);
}

int cace_exact_mesh_counts(
    void* raw_handle,
    int* out_vertices,
    int* out_triangles,
    int* out_edges,
    int* out_interior_edges,
    int* out_boundary_edges) {
    try {
        if (!raw_handle || !out_vertices || !out_triangles || !out_edges ||
            !out_interior_edges || !out_boundary_edges) return -1;
        const auto& mesh = static_cast<CaceExactMeshHandle*>(raw_handle)->mesh;
        *out_vertices = static_cast<int>(mesh.vertices.size());
        *out_triangles = static_cast<int>(mesh.triangles.size());
        *out_edges = static_cast<int>(mesh.edges.size());
        *out_interior_edges = static_cast<int>(mesh.interior_edge_ids.size());
        *out_boundary_edges = static_cast<int>(mesh.boundary_edge_ids.size());
        return 0;
    } catch (...) {
        return -1;
    }
}

int cace_exact_mesh_signed_jacobian(
    void* raw_handle,
    int cell,
    std::int64_t* out_numerator,
    std::int64_t* out_denominator) {
    try {
        if (!raw_handle || !out_numerator || !out_denominator || cell < 0) return -1;
        const auto& mesh = static_cast<CaceExactMeshHandle*>(raw_handle)->mesh;
        const auto& value = mesh.signed_jacobians.at(static_cast<std::size_t>(cell));
        *out_numerator = value.numerator();
        *out_denominator = value.denominator();
        return 0;
    } catch (...) {
        return -1;
    }
}

int cace_exact_assembly_status(
    void* raw_handle,
    const std::int64_t* p1_numerators,
    const std::int64_t* p1_denominators,
    const std::int64_t* rt0_numerators,
    const std::int64_t* rt0_denominators,
    int cell_count,
    int* out_ready,
    int* out_local_green,
    int* out_equilibrium_failures,
    int* out_boundary_failures,
    int* out_interior_failures) {
    try {
        if (!raw_handle || !p1_numerators || !p1_denominators ||
            !rt0_numerators || !rt0_denominators || !out_ready ||
            !out_local_green || !out_equilibrium_failures ||
            !out_boundary_failures || !out_interior_failures) return -1;
        if (cell_count < 0) return -1;

        const auto& mesh = static_cast<CaceExactMeshHandle*>(raw_handle)->mesh;
        if (static_cast<std::size_t>(cell_count) != mesh.triangles.size()) return -2;

        std::vector<cace::exact::P1Affine> primal;
        std::vector<cace::exact::RT0Affine> flux;
        primal.reserve(static_cast<std::size_t>(cell_count));
        flux.reserve(static_cast<std::size_t>(cell_count));

        for (int cell = 0; cell < cell_count; ++cell) {
            const std::size_t i = static_cast<std::size_t>(3 * cell);
            primal.push_back({
                cace::exact::Rational(p1_numerators[i + 0], p1_denominators[i + 0]),
                cace::exact::Rational(p1_numerators[i + 1], p1_denominators[i + 1]),
                cace::exact::Rational(p1_numerators[i + 2], p1_denominators[i + 2]),
            });
            flux.push_back({
                cace::exact::Rational(rt0_numerators[i + 0], rt0_denominators[i + 0]),
                cace::exact::Rational(rt0_numerators[i + 1], rt0_denominators[i + 1]),
                cace::exact::Rational(rt0_numerators[i + 2], rt0_denominators[i + 2]),
            });
        }

        const auto status = cace::exact::exact_assembly_obligations(mesh, primal, flux);
        int equilibrium_failures = 0;
        int boundary_failures = 0;
        int interior_failures = 0;
        for (const bool value : status.equilibrium) if (!value) ++equilibrium_failures;
        for (const bool value : status.boundary_admissible) if (!value) ++boundary_failures;
        for (const bool value : status.interior_cancellation) if (!value) ++interior_failures;

        *out_ready = status.ready_for_lean_assembly ? 1 : 0;
        *out_local_green = status.all_local_green ? 1 : 0;
        *out_equilibrium_failures = equilibrium_failures;
        *out_boundary_failures = boundary_failures;
        *out_interior_failures = interior_failures;
        return 0;
    } catch (...) {
        return -1;
    }
}

int cace_exact_cell_values(
    void* raw_handle,
    const std::int64_t* p1_numerators,
    const std::int64_t* p1_denominators,
    const std::int64_t* rt0_numerators,
    const std::int64_t* rt0_denominators,
    int cell,
    std::int64_t* out_numerators,
    std::int64_t* out_denominators,
    int out_capacity) {
    try {
        if (!raw_handle || !p1_numerators || !p1_denominators ||
            !rt0_numerators || !rt0_denominators || !out_numerators ||
            !out_denominators || cell < 0) return -1;
        if (out_capacity < 5) return -3;

        const auto& mesh = static_cast<CaceExactMeshHandle*>(raw_handle)->mesh;
        const std::size_t k = static_cast<std::size_t>(cell);
        const auto triangle = mesh.triangle(k);
        const std::size_t i = 3 * k;

        const cace::exact::P1Affine p{
            cace::exact::Rational(p1_numerators[i + 0], p1_denominators[i + 0]),
            cace::exact::Rational(p1_numerators[i + 1], p1_denominators[i + 1]),
            cace::exact::Rational(p1_numerators[i + 2], p1_denominators[i + 2]),
        };
        const cace::exact::RT0Affine q{
            cace::exact::Rational(rt0_numerators[i + 0], rt0_denominators[i + 0]),
            cace::exact::Rational(rt0_numerators[i + 1], rt0_denominators[i + 1]),
            cace::exact::Rational(rt0_numerators[i + 2], rt0_denominators[i + 2]),
        };

        const std::array<cace::exact::Rational, 5> values{{
            cace::exact::cell_pairing(triangle, p, q),
            cace::exact::cell_divergence(triangle, p, q),
            cace::exact::local_face_pairing(triangle, p, q, 0),
            cace::exact::local_face_pairing(triangle, p, q, 1),
            cace::exact::local_face_pairing(triangle, p, q, 2),
        }};

        for (std::size_t j = 0; j < values.size(); ++j) {
            out_numerators[j] = values[j].numerator();
            out_denominators[j] = values[j].denominator();
        }
        return 0;
    } catch (...) {
        return -1;
    }
}

const char* cace_runtime_version(){ return "0.21.0"; }
}
