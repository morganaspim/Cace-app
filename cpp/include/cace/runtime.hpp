#pragma once
#include <vector>
#include <stdexcept>
#include <cmath>
#include <algorithm>
#include <numeric>
#include <utility>
#include <map>
#include <set>
#include <tuple>
#include <future>
#include <chrono>
#include <limits>
namespace cace {
inline double dot(const std::vector<double>& a, const std::vector<double>& b) {
    if (a.size() != b.size()) throw std::invalid_argument("size mismatch");
    double s = 0.0; for (std::size_t i=0;i<a.size();++i) s += a[i]*b[i]; return s;
}
inline std::vector<double> csr_matvec(const std::vector<double>& data,const std::vector<int>& indices,const std::vector<int>& indptr,const std::vector<double>& x) {
    if (indptr.empty()) return {}; const std::size_t n=indptr.size()-1; std::vector<double> y(n,0.0);
    for(std::size_t i=0;i<n;++i){ if(indptr[i]<0||indptr[i+1]<indptr[i]) throw std::invalid_argument("invalid CSR row pointer");
        for(int p=indptr[i];p<indptr[i+1];++p){ int j=indices.at((std::size_t)p); if(j<0||(std::size_t)j>=x.size()) throw std::invalid_argument("CSR column out of range"); y[i]+=data.at((std::size_t)p)*x[(std::size_t)j]; }}
    return y;
}
inline std::vector<double> csr_residual(const std::vector<double>& data,const std::vector<int>& indices,const std::vector<int>& indptr,const std::vector<double>& x,const std::vector<double>& b){
    auto y=csr_matvec(data,indices,indptr,x); if(y.size()!=b.size()) throw std::invalid_argument("rhs size mismatch"); for(std::size_t i=0;i<y.size();++i)y[i]-=b[i]; return y;
}
inline double csr_residual_inf(const std::vector<double>& data,const std::vector<int>& indices,const std::vector<int>& indptr,const std::vector<double>& x,const std::vector<double>& b){
    auto r=csr_residual(data,indices,indptr,x,b); double n=0.0; for(double v:r)n=std::max(n,std::abs(v)); return n;
}
inline std::vector<int> dorfler_mark(const std::vector<double>& eta,double theta){
    if(!(theta>0.0&&theta<=1.0)) throw std::invalid_argument("theta must be in (0,1]"); std::vector<std::size_t> order(eta.size()); std::iota(order.begin(),order.end(),0); std::vector<double>w(eta.size()); double total=0.0;
    for(std::size_t i=0;i<eta.size();++i){ if(!std::isfinite(eta[i])||eta[i]<0) throw std::invalid_argument("invalid estimator"); w[i]=eta[i]*eta[i]; total+=w[i]; }
    std::stable_sort(order.begin(),order.end(),[&](std::size_t a,std::size_t b){ return w[a]==w[b]?a<b:w[a]>w[b]; }); double target=theta*total,acc=0.0; std::vector<int>out;
    for(auto k:order){out.push_back((int)k);acc+=w[k];if(acc>=target)break;} std::sort(out.begin(),out.end()); return out;
}
inline void p1_1d_reduced_stiffness(const std::vector<double>& nodes,std::vector<double>& data,std::vector<int>& indices,std::vector<int>& indptr){
    if(nodes.size()<2) throw std::invalid_argument("at least two nodes required"); for(std::size_t i=0;i+1<nodes.size();++i) if(!(nodes[i+1]>nodes[i])) throw std::invalid_argument("nodes must be strictly increasing");
    int ni=(int)nodes.size()-2; std::vector<std::vector<std::pair<int,double>>> rows((std::size_t)std::max(ni,0));
    auto add_entry=[&](int i,int j,double v){auto&r=rows.at((std::size_t)i);for(auto&kv:r)if(kv.first==j){kv.second+=v;return;}r.push_back({j,v});};
    for(int e=0;e<(int)nodes.size()-1;++e){double inv=1.0/(nodes[e+1]-nodes[e]); int gv[2]={e,e+1}; double loc[2][2]={{inv,-inv},{-inv,inv}};
        for(int a=0;a<2;++a){if(gv[a]==0||gv[a]==(int)nodes.size()-1)continue;int i=gv[a]-1;for(int b=0;b<2;++b){if(gv[b]==0||gv[b]==(int)nodes.size()-1)continue;int j=gv[b]-1;add_entry(i,j,loc[a][b]);}}}
    data.clear();indices.clear();indptr.clear();indptr.push_back(0);for(auto&r:rows){std::sort(r.begin(),r.end(),[](auto&a,auto&b){return a.first<b.first;});for(auto&kv:r)if(kv.second!=0.0){indices.push_back(kv.first);data.push_back(kv.second);}indptr.push_back((int)data.size());}
}

struct SparseLDLTStats { int factor_nnz=0; int fill_edges=0; double min_pivot=0.0; bool success=false; };
inline SparseLDLTStats sparse_ldlt_stats(const std::vector<double>& data,const std::vector<int>& indices,const std::vector<int>& indptr,const std::vector<int>& order){
    const int n=(int)order.size(); if((int)indptr.size()!=n+1) throw std::invalid_argument("order/CSR size mismatch");
    std::vector<int> inv(n); std::vector<char> seen(n,0); for(int ni=0;ni<n;++ni){int oi=order[ni]; if(oi<0||oi>=n||seen[oi]) throw std::invalid_argument("invalid ordering"); seen[oi]=1; inv[oi]=ni;}
    std::vector<std::map<int,double>> A(n); for(int oi=0;oi<n;++oi) for(int p=indptr[oi];p<indptr[oi+1];++p) A[inv[oi]][inv[indices[p]]] += data[p];
    for(int i=0;i<n;++i) for(auto &kv:A[i]) if(std::abs(A[kv.first][i]-kv.second)>1e-12) return {};
    std::vector<std::set<int>> work(n),pat(n); for(int i=0;i<n;++i) for(auto &kv:A[i]) if(kv.first!=i&&kv.second!=0){work[i].insert(kv.first);work[kv.first].insert(i);} std::set<int> active; for(int i=0;i<n;++i)active.insert(i); int fill=0;
    for(int i=0;i<n;++i){ std::vector<int> nbr; for(int j:work[i]) if(active.count(j)&&j>i) nbr.push_back(j); for(int j:nbr)pat[j].insert(i); for(size_t a=0;a<nbr.size();++a)for(size_t b=a+1;b<nbr.size();++b)if(!work[nbr[a]].count(nbr[b])){work[nbr[a]].insert(nbr[b]);work[nbr[b]].insert(nbr[a]);++fill;} active.erase(i); }
    std::vector<std::map<int,double>> L(n); std::vector<double>D(n); double minp=std::numeric_limits<double>::infinity();
    for(int i=0;i<n;++i){ double acc=0; for(int k:pat[i])acc+=L[i][k]*L[i][k]*D[k]; double piv=A[i][i]-acc; if(!(piv>0)||!std::isfinite(piv)) return {}; D[i]=piv; minp=std::min(minp,piv); for(int j=i+1;j<n;++j)if(pat[j].count(i)){double a2=0; for(int k:pat[j])if(k<i&&pat[i].count(k))a2+=L[j][k]*L[i][k]*D[k]; L[j][i]=(A[j].count(i)?A[j][i]:0.0)-a2; L[j][i]/=D[i];}}
    SparseLDLTStats out; out.factor_nnz=n; for(auto&p:pat)out.factor_nnz+=(int)p.size(); out.fill_edges=fill; out.min_pivot=minp; out.success=true; return out;
}

}

namespace cace {
struct SparseSolveResult { std::vector<double> x; int factor_nnz=0; int fill_edges=0; double min_pivot=0.0; bool success=false; };
inline SparseSolveResult sparse_ldlt_solve(const std::vector<double>& data,const std::vector<int>& indices,const std::vector<int>& indptr,const std::vector<int>& order,const std::vector<double>& b){
    const int n=(int)order.size(); if((int)indptr.size()!=n+1 || (int)b.size()!=n) throw std::invalid_argument("size mismatch");
    std::vector<int> inv(n); std::vector<char> seen(n,0); for(int ni=0;ni<n;++ni){int oi=order[ni]; if(oi<0||oi>=n||seen[oi]) throw std::invalid_argument("invalid ordering"); seen[oi]=1; inv[oi]=ni;}
    std::vector<std::map<int,double>> A(n); for(int oi=0;oi<n;++oi) for(int p=indptr[oi];p<indptr[oi+1];++p) A[inv[oi]][inv[indices[p]]] += data[p];
    for(int i=0;i<n;++i) for(auto &kv:A[i]) if(std::abs(A[kv.first][i]-kv.second)>1e-12) return {};
    std::vector<std::set<int>> work(n),pat(n); for(int i=0;i<n;++i) for(auto &kv:A[i]) if(kv.first!=i&&kv.second!=0){work[i].insert(kv.first);work[kv.first].insert(i);} std::set<int> active; for(int i=0;i<n;++i)active.insert(i); int fill=0;
    for(int i=0;i<n;++i){std::vector<int> nbr;for(int j:work[i])if(active.count(j)&&j>i)nbr.push_back(j);for(int j:nbr)pat[j].insert(i);for(size_t a=0;a<nbr.size();++a)for(size_t bb=a+1;bb<nbr.size();++bb)if(!work[nbr[a]].count(nbr[bb])){work[nbr[a]].insert(nbr[bb]);work[nbr[bb]].insert(nbr[a]);++fill;}active.erase(i);}
    std::vector<std::map<int,double>> L(n); std::vector<double>D(n); double minp=std::numeric_limits<double>::infinity();
    for(int i=0;i<n;++i){double acc=0;for(int k:pat[i])acc+=L[i][k]*L[i][k]*D[k];double piv=A[i][i]-acc;if(!(piv>0)||!std::isfinite(piv))return {};D[i]=piv;minp=std::min(minp,piv);for(int j=i+1;j<n;++j)if(pat[j].count(i)){double a2=0;for(int k:pat[j])if(k<i&&pat[i].count(k))a2+=L[j][k]*L[i][k]*D[k];L[j][i]=((A[j].count(i)?A[j][i]:0.0)-a2)/D[i];}}
    std::vector<double> bp(n);for(int ni=0;ni<n;++ni)bp[ni]=b[order[ni]];
    std::vector<double> y=bp; for(int i=0;i<n;++i) for(auto &kv:L[i]) y[i]-=kv.second*y[kv.first];
    std::vector<double> z(n);for(int i=0;i<n;++i)z[i]=y[i]/D[i];
    std::vector<double> xp=z; for(int i=n-1;i>=0;--i) for(int j=i+1;j<n;++j){auto it=L[j].find(i);if(it!=L[j].end())xp[i]-=it->second*xp[j];}
    std::vector<double> x(n);for(int ni=0;ni<n;++ni)x[order[ni]]=xp[ni];
    SparseSolveResult out;out.x=x;out.factor_nnz=n;for(auto&p:pat)out.factor_nnz+=(int)p.size();out.fill_edges=fill;out.min_pivot=minp;out.success=true;return out;
}
}


namespace cace {
struct MultifrontalSolveResult {
    std::vector<double> x;
    int factor_nnz=0;
    int fill_edges=0;
    double min_pivot=0.0;
    int peak_front_size=0;
    long long total_front_entries=0;
    int parallel_tasks=0;
    double factor_solve_ms=0.0;
    bool success=false;
};

struct MFSubtree {
    std::vector<std::tuple<int,int,double>> l_entries;
    std::vector<std::pair<int,double>> d_entries;
    std::vector<int> update;
    std::vector<double> schur; // row-major on update x update
    double min_pivot=std::numeric_limits<double>::infinity();
    int peak_front_size=0;
    long long total_front_entries=0;
    int parallel_tasks=0;
    bool success=true;
};

inline MultifrontalSolveResult sparse_multifrontal_ldlt_solve(
    const std::vector<double>& data,const std::vector<int>& indices,const std::vector<int>& indptr,
    const std::vector<int>& order,const std::vector<double>& b,int max_parallel_depth=2)
{
    auto t0=std::chrono::steady_clock::now();
    const int n=(int)order.size();
    if((int)indptr.size()!=n+1 || (int)b.size()!=n) throw std::invalid_argument("size mismatch");
    std::vector<int> inv(n); std::vector<char> seen(n,0);
    for(int ni=0;ni<n;++ni){int oi=order[ni]; if(oi<0||oi>=n||seen[oi]) throw std::invalid_argument("invalid ordering"); seen[oi]=1; inv[oi]=ni;}
    std::vector<std::map<int,double>> A(n);
    for(int oi=0;oi<n;++oi) for(int p=indptr[oi];p<indptr[oi+1];++p) A[inv[oi]][inv[indices[p]]] += data[p];
    for(int i=0;i<n;++i) for(auto &kv:A[i]) if(std::abs(A[kv.first][i]-kv.second)>1e-12) return {};

    // Symbolic filled graph and lower factor pattern.
    std::vector<std::set<int>> work(n),pat(n);
    for(int i=0;i<n;++i) for(auto &kv:A[i]) if(kv.first!=i&&kv.second!=0){work[i].insert(kv.first);work[kv.first].insert(i);}
    std::set<int> active; for(int i=0;i<n;++i) active.insert(i); int fill=0;
    for(int i=0;i<n;++i){
        std::vector<int> nbr; for(int j:work[i]) if(active.count(j)&&j>i) nbr.push_back(j);
        for(int j:nbr) pat[j].insert(i);
        for(size_t a=0;a<nbr.size();++a) for(size_t bb=a+1;bb<nbr.size();++bb)
            if(!work[nbr[a]].count(nbr[bb])){work[nbr[a]].insert(nbr[bb]);work[nbr[bb]].insert(nbr[a]);++fill;}
        active.erase(i);
    }
    // Elimination tree: parent(j) is the smallest higher row containing L(row,j).
    std::vector<int> parent(n,-1); std::vector<std::vector<int>> children(n);
    for(int j=0;j<n;++j){int p=-1; for(int i=j+1;i<n;++i) if(pat[i].count(j)){p=i;break;} parent[j]=p; if(p>=0)children[p].push_back(j);}
    std::vector<int> roots; for(int j=0;j<n;++j) if(parent[j]<0) roots.push_back(j);

    std::function<MFSubtree(int,int)> factor_node;
    factor_node = [&](int j,int depth)->MFSubtree {
        MFSubtree out;
        std::vector<MFSubtree> child_results;
        child_results.reserve(children[j].size());
        if(depth<max_parallel_depth && children[j].size()>1){
            std::vector<std::future<MFSubtree>> fut;
            for(int c:children[j]) fut.push_back(std::async(std::launch::async,[&,c,depth](){return factor_node(c,depth+1);}));
            out.parallel_tasks += (int)fut.size();
            for(auto &f:fut) child_results.push_back(f.get());
        } else {
            for(int c:children[j]) child_results.push_back(factor_node(c,depth+1));
        }
        for(auto &cr:child_results){ if(!cr.success){out.success=false;return out;} out.parallel_tasks+=cr.parallel_tasks; out.peak_front_size=std::max(out.peak_front_size,cr.peak_front_size); out.total_front_entries+=cr.total_front_entries; out.min_pivot=std::min(out.min_pivot,cr.min_pivot); out.l_entries.insert(out.l_entries.end(),cr.l_entries.begin(),cr.l_entries.end()); out.d_entries.insert(out.d_entries.end(),cr.d_entries.begin(),cr.d_entries.end()); }

        std::vector<int> upd; for(int i=j+1;i<n;++i) if(pat[i].count(j)) upd.push_back(i);
        std::vector<int> vars; vars.push_back(j); vars.insert(vars.end(),upd.begin(),upd.end());
        const int m=(int)vars.size(); out.peak_front_size=std::max(out.peak_front_size,m); out.total_front_entries+=(long long)m*m;
        std::map<int,int> pos; for(int q=0;q<m;++q)pos[vars[q]]=q;
        std::vector<double> F((size_t)m*m,0.0);
        auto addF=[&](int r,int c,double v){F[(size_t)r*m+c]+=v;};
        auto aval=[&](int r,int c){auto it=A[r].find(c);return it==A[r].end()?0.0:it->second;};
        addF(0,0,aval(j,j));
        for(int q=1;q<m;++q){double v=aval(vars[q],j);addF(q,0,v);addF(0,q,v);}
        for(auto &cr:child_results){
            int k=(int)cr.update.size();
            for(int a=0;a<k;++a){ auto ia=pos.find(cr.update[a]); if(ia==pos.end()){out.success=false;return out;} for(int bb=0;bb<k;++bb){auto ib=pos.find(cr.update[bb]); if(ib==pos.end()){out.success=false;return out;} addF(ia->second,ib->second,cr.schur[(size_t)a*k+bb]);}}
        }
        double d=F[0]; if(!(d>0)||!std::isfinite(d)){out.success=false;return out;}
        out.min_pivot=std::min(out.min_pivot,d); out.d_entries.push_back({j,d});
        std::vector<double> l(m,0.0); l[0]=1.0;
        for(int q=1;q<m;++q){l[q]=F[(size_t)q*m]/d; out.l_entries.push_back({vars[q],j,l[q]});}
        const int k=m-1; out.update=upd; out.schur.assign((size_t)k*k,0.0);
        for(int a=0;a<k;++a) for(int bb=0;bb<k;++bb) out.schur[(size_t)a*k+bb]=F[(size_t)(a+1)*m+(bb+1)]-l[a+1]*d*l[bb+1];
        return out;
    };

    std::vector<MFSubtree> rr; rr.reserve(roots.size());
    if(roots.size()>1 && max_parallel_depth>0){
        std::vector<std::future<MFSubtree>> fut;
        for(int r:roots) fut.push_back(std::async(std::launch::async,[&,r](){return factor_node(r,1);}));
        for(auto &f:fut) rr.push_back(f.get());
    } else for(int r:roots) rr.push_back(factor_node(r,0));
    std::vector<std::map<int,double>> L(n); std::vector<double>D(n,0.0); double minp=std::numeric_limits<double>::infinity(); int peak=0,tasks=(roots.size()>1&&max_parallel_depth>0)?(int)roots.size():0; long long total_front=0;
    for(auto &r:rr){ if(!r.success || !r.update.empty()) return {}; tasks+=r.parallel_tasks; peak=std::max(peak,r.peak_front_size);total_front+=r.total_front_entries;minp=std::min(minp,r.min_pivot);for(auto &e:r.l_entries){int i,j;double v;std::tie(i,j,v)=e;L[i][j]=v;}for(auto &dv:r.d_entries)D[dv.first]=dv.second; }
    for(double d:D) if(!(d>0)) return {};

    std::vector<double> bp(n);for(int ni=0;ni<n;++ni)bp[ni]=b[order[ni]];
    std::vector<double> y=bp;for(int i=0;i<n;++i)for(auto&kv:L[i])y[i]-=kv.second*y[kv.first];
    std::vector<double> z(n);for(int i=0;i<n;++i)z[i]=y[i]/D[i];
    std::vector<double> xp=z;for(int i=n-1;i>=0;--i)for(int j=i+1;j<n;++j){auto it=L[j].find(i);if(it!=L[j].end())xp[i]-=it->second*xp[j];}
    std::vector<double>x(n);for(int ni=0;ni<n;++ni)x[order[ni]]=xp[ni];
    auto t1=std::chrono::steady_clock::now();
    MultifrontalSolveResult res;res.x=x;res.factor_nnz=n;for(auto&p:pat)res.factor_nnz+=(int)p.size();res.fill_edges=fill;res.min_pivot=minp;res.peak_front_size=peak;res.total_front_entries=total_front;res.parallel_tasks=tasks;res.factor_solve_ms=std::chrono::duration<double,std::milli>(t1-t0).count();res.success=true;return res;
}
}

#include <thread>
#include <mutex>
#include <condition_variable>
#include <queue>
#include <atomic>

namespace cace {

class FixedThreadPool {
public:
    explicit FixedThreadPool(int threads): stop_(false) {
        int nt=std::max(1,threads);
        for(int i=0;i<nt;++i) workers_.emplace_back([this](){
            for(;;){
                std::function<void()> task;
                {
                    std::unique_lock<std::mutex> lk(mu_);
                    cv_.wait(lk,[&](){return stop_||!q_.empty();});
                    if(stop_&&q_.empty()) return;
                    task=std::move(q_.front()); q_.pop();
                }
                task();
            }
        });
    }
    ~FixedThreadPool(){
        { std::lock_guard<std::mutex> lk(mu_); stop_=true; }
        cv_.notify_all(); for(auto &t:workers_) if(t.joinable()) t.join();
    }
    template<class F> auto submit(F f)->std::future<decltype(f())>{
        using R=decltype(f()); auto p=std::make_shared<std::packaged_task<R()>>(std::move(f)); auto fut=p->get_future();
        {std::lock_guard<std::mutex>lk(mu_); q_.push([p](){(*p)();});} cv_.notify_one(); return fut;
    }
private:
    std::vector<std::thread> workers_; std::queue<std::function<void()>> q_; std::mutex mu_; std::condition_variable cv_; bool stop_;
};

struct SupernodalSolveResult {
    std::vector<double> x;
    int factor_nnz=0, fill_edges=0; double min_pivot=0.0;
    int supernodes=0, max_supernode_size=0, peak_front_size=0;
    long long total_front_entries=0, block_flop_proxy=0;
    int thread_count=1, scheduled_tasks=0, workspace_reallocations=0;
    long long peak_workspace_entries=0;
    double factor_solve_ms=0.0; bool success=false;
};

struct SNNodeResult {
    std::vector<std::tuple<int,int,double>> l_entries;
    std::vector<std::pair<int,double>> d_entries;
    std::vector<int> update;
    std::vector<double> schur;
    double min_pivot=std::numeric_limits<double>::infinity();
    int peak_front_size=0; long long total_front_entries=0, block_flop_proxy=0;
    bool success=true;
};

inline SupernodalSolveResult sparse_supernodal_ldlt_solve(
    const std::vector<double>& data,const std::vector<int>& indices,const std::vector<int>& indptr,
    const std::vector<int>& order,const std::vector<double>& b,int requested_threads=0)
{
    auto t0=std::chrono::steady_clock::now(); const int n=(int)order.size();
    if((int)indptr.size()!=n+1||(int)b.size()!=n) throw std::invalid_argument("size mismatch");
    std::vector<int> inv(n);std::vector<char>seen(n,0);for(int ni=0;ni<n;++ni){int oi=order[ni];if(oi<0||oi>=n||seen[oi])throw std::invalid_argument("invalid ordering");seen[oi]=1;inv[oi]=ni;}
    std::vector<std::map<int,double>> A(n);for(int oi=0;oi<n;++oi)for(int p=indptr[oi];p<indptr[oi+1];++p)A[inv[oi]][inv[indices[p]]]+=data[p];
    for(int i=0;i<n;++i)for(auto&kv:A[i])if(std::abs(A[kv.first][i]-kv.second)>1e-12)return {};
    std::vector<std::set<int>> work(n),pat(n);for(int i=0;i<n;++i)for(auto&kv:A[i])if(kv.first!=i&&kv.second!=0){work[i].insert(kv.first);work[kv.first].insert(i);}std::set<int>active;for(int i=0;i<n;++i)active.insert(i);int fill=0;
    for(int i=0;i<n;++i){std::vector<int>nbr;for(int j:work[i])if(active.count(j)&&j>i)nbr.push_back(j);for(int j:nbr)pat[j].insert(i);for(size_t a=0;a<nbr.size();++a)for(size_t bb=a+1;bb<nbr.size();++bb)if(!work[nbr[a]].count(nbr[bb])){work[nbr[a]].insert(nbr[bb]);work[nbr[bb]].insert(nbr[a]);++fill;}active.erase(i);}
    std::vector<int> parent(n,-1);for(int j=0;j<n;++j)for(int i=j+1;i<n;++i)if(pat[i].count(j)){parent[j]=i;break;}
    // Structural supernodes: merge consecutive columns j,j+1 iff parent(j)=j+1 and tails beyond j+1 match.
    std::vector<std::vector<int>> groups;for(int j=0;j<n;){std::vector<int>g{j};while(j+1<n&&parent[j]==j+1){std::set<int>a,b2;for(int r=j+2;r<n;++r){if(pat[r].count(j))a.insert(r);if(pat[r].count(j+1))b2.insert(r);}if(a!=b2)break;++j;g.push_back(j);}groups.push_back(g);++j;}
    const int ns=(int)groups.size();std::vector<int>col_group(n,-1);for(int s=0;s<ns;++s)for(int c:groups[s])col_group[c]=s;
    std::vector<int> sparent(ns,-1);std::vector<std::vector<int>>children(ns);for(int s=0;s<ns;++s){int last=groups[s].back(),p=parent[last];if(p>=0){int sp=col_group[p];if(sp==s)return {};sparent[s]=sp;children[sp].push_back(s);}}
    std::vector<int> level(ns,0);std::function<int(int)> lev=[&](int s){int m=0;for(int c:children[s])m=std::max(m,lev(c)+1);return level[s]=m;};for(int s=0;s<ns;++s)if(sparent[s]<0)lev(s);int maxlev=*std::max_element(level.begin(),level.end());
    int threads=requested_threads>0?requested_threads:(int)std::thread::hardware_concurrency();threads=std::max(1,threads);FixedThreadPool pool(threads);
    std::vector<SNNodeResult> results(ns);std::atomic<int> reallocs{0};std::atomic<long long>peak_ws{0};std::atomic<int>tasks{0};
    auto factor_super=[&](int s)->SNNodeResult {
        tasks.fetch_add(1); SNNodeResult out; const auto&S=groups[s];int k=(int)S.size();
        std::set<int>uset;int send=S.back();for(int c:S)for(int r=send+1;r<n;++r)if(pat[r].count(c))uset.insert(r);std::vector<int>U(uset.begin(),uset.end()),vars=S;vars.insert(vars.end(),U.begin(),U.end());int m=(int)vars.size();
        out.peak_front_size=m;out.total_front_entries=(long long)m*m;out.block_flop_proxy+=(long long)k*k*k + (long long)std::max(0,m-k)*k*k + (long long)std::max(0,m-k)*std::max(0,m-k)*k;
        thread_local std::vector<double> ws;if((int)ws.size()<m*m){ws.resize((size_t)m*m);reallocs.fetch_add(1);}std::fill(ws.begin(),ws.begin()+(size_t)m*m,0.0);long long want=(long long)m*m,old=peak_ws.load();while(want>old&&!peak_ws.compare_exchange_weak(old,want)){}
        auto F=[&](int r,int c)->double&{return ws[(size_t)r*m+c];};std::map<int,int>pos;for(int q=0;q<m;++q)pos[vars[q]]=q;
        // Original A entries with at least one pivot index; never add U-U originals here.
        for(int a=0;a<k;++a){int ca=S[a];for(int bb=0;bb<k;++bb){int cb=S[bb];auto it=A[ca].find(cb);if(it!=A[ca].end())F(a,bb)+=it->second;}for(int q=k;q<m;++q){int ur=vars[q];auto it=A[ur].find(ca);double v=it==A[ur].end()?0.0:it->second;F(q,a)+=v;F(a,q)+=v;}}
        for(int c:children[s]){auto&cr=results[c];if(!cr.success){out.success=false;return out;}out.min_pivot=std::min(out.min_pivot,cr.min_pivot);out.peak_front_size=std::max(out.peak_front_size,cr.peak_front_size);out.total_front_entries+=cr.total_front_entries;out.block_flop_proxy+=cr.block_flop_proxy;int ku=(int)cr.update.size();for(int a=0;a<ku;++a){auto ia=pos.find(cr.update[a]);if(ia==pos.end()){out.success=false;return out;}for(int bb=0;bb<ku;++bb){auto ib=pos.find(cr.update[bb]);if(ib==pos.end()){out.success=false;return out;}F(ia->second,ib->second)+=cr.schur[(size_t)a*ku+bb];}}out.l_entries.insert(out.l_entries.end(),cr.l_entries.begin(),cr.l_entries.end());out.d_entries.insert(out.d_entries.end(),cr.d_entries.begin(),cr.d_entries.end());}
        // Dense block LDL on leading supernode pivots, with dense update rows.
        std::vector<double>Dloc(k,0.0);std::vector<double>Lloc((size_t)m*k,0.0);for(int a=0;a<k;++a)Lloc[(size_t)a*k+a]=1.0;
        for(int p=0;p<k;++p){double d=F(p,p);for(int r=0;r<p;++r){double l=Lloc[(size_t)p*k+r];d-=l*l*Dloc[r];}if(!(d>0)||!std::isfinite(d)){out.success=false;return out;}Dloc[p]=d;out.min_pivot=std::min(out.min_pivot,d);out.d_entries.push_back({S[p],d});for(int q=p+1;q<m;++q){double v=F(q,p);for(int r=0;r<p;++r)v-=Lloc[(size_t)q*k+r]*Lloc[(size_t)p*k+r]*Dloc[r];double l=v/d;Lloc[(size_t)q*k+p]=l;out.l_entries.push_back({vars[q],S[p],l});}}
        int nu=m-k;out.update=U;out.schur.assign((size_t)nu*nu,0.0);for(int a=0;a<nu;++a)for(int bb=0;bb<nu;++bb){double v=F(k+a,k+bb);for(int p=0;p<k;++p)v-=Lloc[(size_t)(k+a)*k+p]*Dloc[p]*Lloc[(size_t)(k+bb)*k+p];out.schur[(size_t)a*nu+bb]=v;}
        return out;
    };
    for(int lv=0;lv<=maxlev;++lv){std::vector<std::future<std::pair<int,SNNodeResult>>> fut;for(int s=0;s<ns;++s)if(level[s]==lv)fut.push_back(pool.submit([&,s](){return std::make_pair(s,factor_super(s));}));for(auto&f:fut){auto pr=f.get();results[pr.first]=std::move(pr.second);if(!results[pr.first].success)return {};}}
    std::vector<std::map<int,double>>L(n);std::vector<double>D(n,0.0);double minp=std::numeric_limits<double>::infinity();int peak=0;long long total=0,flops=0;for(int s=0;s<ns;++s){auto&r=results[s];peak=std::max(peak,r.peak_front_size);total+=r.total_front_entries;flops+=r.block_flop_proxy;minp=std::min(minp,r.min_pivot);for(auto&e:r.l_entries){int i,j;double v;std::tie(i,j,v)=e;L[i][j]=v;}for(auto&dv:r.d_entries)D[dv.first]=dv.second;}for(double d:D)if(!(d>0))return {};
    std::vector<double>bp(n);for(int ni=0;ni<n;++ni)bp[ni]=b[order[ni]];std::vector<double>y=bp;for(int i=0;i<n;++i)for(auto&kv:L[i])y[i]-=kv.second*y[kv.first];std::vector<double>z(n);for(int i=0;i<n;++i)z[i]=y[i]/D[i];std::vector<double>xp=z;for(int i=n-1;i>=0;--i)for(int j=i+1;j<n;++j){auto it=L[j].find(i);if(it!=L[j].end())xp[i]-=it->second*xp[j];}std::vector<double>x(n);for(int ni=0;ni<n;++ni)x[order[ni]]=xp[ni];
    auto t1=std::chrono::steady_clock::now();SupernodalSolveResult out;out.x=x;out.factor_nnz=n;for(auto&p:pat)out.factor_nnz+=(int)p.size();out.fill_edges=fill;out.min_pivot=minp;out.supernodes=ns;for(auto&g:groups)out.max_supernode_size=std::max(out.max_supernode_size,(int)g.size());out.peak_front_size=peak;out.total_front_entries=total;out.block_flop_proxy=flops;out.thread_count=threads;out.scheduled_tasks=tasks.load();out.workspace_reallocations=reallocs.load();out.peak_workspace_entries=peak_ws.load();out.factor_solve_ms=std::chrono::duration<double,std::milli>(t1-t0).count();out.success=true;return out;
}
}
