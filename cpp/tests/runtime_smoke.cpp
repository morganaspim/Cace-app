#include "cace/runtime.hpp"
#include <iostream>
#include <cmath>
int main(){
 std::vector<double>d{2,-1,-1,2}; std::vector<int>ix{0,1,0,1}; std::vector<int>ip{0,2,4}; std::vector<double>x{1,2},b{0,3};
 auto y=cace::csr_matvec(d,ix,ip,x); if(y.size()!=2 || std::abs(y[0])>1e-15 || std::abs(y[1]-3)>1e-15) return 2;
 if(cace::csr_residual_inf(d,ix,ip,x,b)>1e-15) return 3;
 auto m=cace::dorfler_mark({1.0,2.0,0.5},0.5); if(m.size()!=1 || m[0]!=1) return 4;
 auto sol=cace::sparse_ldlt_solve(d,ix,ip,{0,1},b); if(!sol.success || sol.x.size()!=2 || std::abs(sol.x[0]-1)>1e-12 || std::abs(sol.x[1]-2)>1e-12) return 5;
 std::cout<<"cace-native-runtime-v0.20 PASS\n"; return 0;
}
