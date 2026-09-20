#include <cstdint>
#include <iostream>

extern "C" {
void* cace_exact_mesh_create(
    const std::int64_t* coordinate_numerators,
    const std::int64_t* coordinate_denominators,
    int vertex_count,
    const int* triangle_vertex_ids,
    int triangle_count);
void cace_exact_mesh_destroy(void* raw_handle);
int cace_exact_mesh_counts(
    void* raw_handle,
    int* out_vertices,
    int* out_triangles,
    int* out_edges,
    int* out_interior_edges,
    int* out_boundary_edges);
int cace_exact_mesh_signed_jacobian(
    void* raw_handle,
    int cell,
    std::int64_t* out_numerator,
    std::int64_t* out_denominator);
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
    int* out_interior_failures);
int cace_exact_cell_values(
    void* raw_handle,
    const std::int64_t* p1_numerators,
    const std::int64_t* p1_denominators,
    const std::int64_t* rt0_numerators,
    const std::int64_t* rt0_denominators,
    int cell,
    std::int64_t* out_numerators,
    std::int64_t* out_denominators,
    int out_capacity);
}

static int fail(int code, const char* message) {
    std::cerr << "FAIL " << code << ": " << message << "\n";
    return code;
}

int main() {
    // x0,y0,x1,y1,x2,y2,x3,y3,x4,y4 as exact numerator/denominator pairs.
    const std::int64_t coord_num[] = {0,0, 1,0, 1,1, 0,1, 1,1};
    const std::int64_t coord_den[] = {1,1, 1,1, 1,1, 1,1, 2,2};
    const int triangles[] = {
        0,1,4,
        1,2,4,
        2,3,4,
        3,0,4,
    };

    void* mesh = cace_exact_mesh_create(coord_num, coord_den, 5, triangles, 4);
    if (!mesh) return fail(2, "mesh creation");

    int nv=0, nt=0, ne=0, ni=0, nb=0;
    if (cace_exact_mesh_counts(mesh,&nv,&nt,&ne,&ni,&nb) != 0) {
        cace_exact_mesh_destroy(mesh);
        return fail(3, "mesh counts call");
    }
    if (nv!=5 || nt!=4 || ne!=8 || ni!=4 || nb!=4) {
        cace_exact_mesh_destroy(mesh);
        return fail(4, "mesh counts values");
    }

    for (int cell=0; cell<4; ++cell) {
        std::int64_t n=0,d=0;
        if (cace_exact_mesh_signed_jacobian(mesh,cell,&n,&d) != 0 || n!=1 || d!=2) {
            cace_exact_mesh_destroy(mesh);
            return fail(5, "signed Jacobian");
        }
    }

    const std::int64_t pnum[] = {
         0, 0, 2,
         2,-2, 0,
         2, 0,-2,
         0, 2, 0,
    };
    const std::int64_t pden[] = {
         1,1,1, 1,1,1, 1,1,1, 1,1,1,
    };
    const std::int64_t qnum[] = {
         1,0,0, 1,0,0, 1,0,0, 1,0,0,
    };
    const std::int64_t qden[] = {
         1,1,1, 1,1,1, 1,1,1, 1,1,1,
    };

    int ready=0, green=0, eqf=0, bdf=0, inf=0;
    if (cace_exact_assembly_status(
            mesh,pnum,pden,qnum,qden,4,
            &ready,&green,&eqf,&bdf,&inf) != 0) {
        cace_exact_mesh_destroy(mesh);
        return fail(6, "assembly status call");
    }
    if (!ready || !green || eqf!=0 || bdf!=0 || inf!=0) {
        cace_exact_mesh_destroy(mesh);
        return fail(7, "assembly status values");
    }

    std::int64_t nums[5]{}, dens[5]{};
    if (cace_exact_cell_values(mesh,pnum,pden,qnum,qden,1,nums,dens,5) != 0) {
        cace_exact_mesh_destroy(mesh);
        return fail(8, "cell values call");
    }
    if (nums[0] != -1 || dens[0] != 2) {
        cace_exact_mesh_destroy(mesh);
        return fail(9, "cell pairing value");
    }

    auto changed_qnum = std::array<std::int64_t,12>{
        1,0,1, 1,0,0, 1,0,0, 1,0,0
    };
    ready=green=eqf=bdf=inf=0;
    if (cace_exact_assembly_status(
            mesh,pnum,pden,changed_qnum.data(),qden,4,
            &ready,&green,&eqf,&bdf,&inf) != 0) {
        cace_exact_mesh_destroy(mesh);
        return fail(10, "changed assembly status call");
    }
    if (ready || !green || (eqf+bdf+inf)==0) {
        cace_exact_mesh_destroy(mesh);
        return fail(11, "changed field must fail at least one admissibility obligation");
    }

    cace_exact_mesh_destroy(mesh);
    std::cout << "cace-exact-fem-capi PASS\n";
    return 0;
}
