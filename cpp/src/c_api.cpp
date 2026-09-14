#include "cace/runtime.hpp"
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

const char* cace_runtime_version(){ return "0.20.0"; }
}
