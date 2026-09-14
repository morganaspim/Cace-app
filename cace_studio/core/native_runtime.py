from __future__ import annotations
import ctypes, os, sys
from pathlib import Path
from dataclasses import dataclass
import numpy as np

@dataclass(frozen=True)
class NativeStatus:
    available: bool
    backend: str
    version: str = ''
    path: str = ''
    reason: str = ''

class NativeRuntime:
    """Thin C ABI loader for CACE C++20 reference kernels.

    Correctness certificates never depend on this loader being present. Native
    results are compared with the Python reference path before backend-
    equivalence evidence is emitted.
    """
    def __init__(self):
        self.lib=None; self.status=self._load()

    def _candidates(self):
        env=os.environ.get('CACE_NATIVE_LIB')
        if env: yield Path(env)
        base=Path(__file__).resolve().parents[1]/'native'
        names=['libcace_runtime_capi.so','libcace_runtime_capi.dylib','cace_runtime_capi.dll']
        for n in names: yield base/n
        root=Path(__file__).resolve().parents[2]
        for n in names: yield root/'cpp'/'build'/n

    def _load(self):
        last='native C ABI library not found'
        for p in self._candidates():
            if not p.exists(): continue
            try:
                lib=ctypes.CDLL(str(p))
                lib.cace_runtime_version.restype=ctypes.c_char_p
                lib.cace_csr_matvec.argtypes=[ctypes.POINTER(ctypes.c_double),ctypes.POINTER(ctypes.c_int),ctypes.POINTER(ctypes.c_int),ctypes.c_int,ctypes.c_int,ctypes.POINTER(ctypes.c_double),ctypes.c_int,ctypes.POINTER(ctypes.c_double)]
                lib.cace_csr_residual_inf.argtypes=[ctypes.POINTER(ctypes.c_double),ctypes.POINTER(ctypes.c_int),ctypes.POINTER(ctypes.c_int),ctypes.c_int,ctypes.c_int,ctypes.POINTER(ctypes.c_double),ctypes.c_int,ctypes.POINTER(ctypes.c_double),ctypes.c_int,ctypes.POINTER(ctypes.c_double)]
                lib.cace_dorfler_mark.argtypes=[ctypes.POINTER(ctypes.c_double),ctypes.c_int,ctypes.c_double,ctypes.POINTER(ctypes.c_int),ctypes.c_int,ctypes.POINTER(ctypes.c_int)]
                lib.cace_sparse_ldlt_stats.argtypes=[ctypes.POINTER(ctypes.c_double),ctypes.POINTER(ctypes.c_int),ctypes.POINTER(ctypes.c_int),ctypes.c_int,ctypes.c_int,ctypes.POINTER(ctypes.c_int),ctypes.c_int,ctypes.POINTER(ctypes.c_int),ctypes.POINTER(ctypes.c_int),ctypes.POINTER(ctypes.c_double)]
                lib.cace_sparse_ldlt_solve.argtypes=[ctypes.POINTER(ctypes.c_double),ctypes.POINTER(ctypes.c_int),ctypes.POINTER(ctypes.c_int),ctypes.c_int,ctypes.c_int,ctypes.POINTER(ctypes.c_int),ctypes.c_int,ctypes.POINTER(ctypes.c_double),ctypes.c_int,ctypes.POINTER(ctypes.c_double),ctypes.c_int,ctypes.POINTER(ctypes.c_int),ctypes.POINTER(ctypes.c_int),ctypes.POINTER(ctypes.c_double)]
                lib.cace_sparse_multifrontal_ldlt_solve.argtypes=[ctypes.POINTER(ctypes.c_double),ctypes.POINTER(ctypes.c_int),ctypes.POINTER(ctypes.c_int),ctypes.c_int,ctypes.c_int,ctypes.POINTER(ctypes.c_int),ctypes.c_int,ctypes.POINTER(ctypes.c_double),ctypes.c_int,ctypes.c_int,ctypes.POINTER(ctypes.c_double),ctypes.c_int,ctypes.POINTER(ctypes.c_int),ctypes.POINTER(ctypes.c_int),ctypes.POINTER(ctypes.c_double),ctypes.POINTER(ctypes.c_int),ctypes.POINTER(ctypes.c_longlong),ctypes.POINTER(ctypes.c_int),ctypes.POINTER(ctypes.c_double)]
                lib.cace_sparse_supernodal_ldlt_solve.argtypes=[ctypes.POINTER(ctypes.c_double),ctypes.POINTER(ctypes.c_int),ctypes.POINTER(ctypes.c_int),ctypes.c_int,ctypes.c_int,ctypes.POINTER(ctypes.c_int),ctypes.c_int,ctypes.POINTER(ctypes.c_double),ctypes.c_int,ctypes.c_int,ctypes.POINTER(ctypes.c_double),ctypes.c_int,ctypes.POINTER(ctypes.c_int),ctypes.POINTER(ctypes.c_int),ctypes.POINTER(ctypes.c_double),ctypes.POINTER(ctypes.c_int),ctypes.POINTER(ctypes.c_int),ctypes.POINTER(ctypes.c_int),ctypes.POINTER(ctypes.c_longlong),ctypes.POINTER(ctypes.c_longlong),ctypes.POINTER(ctypes.c_int),ctypes.POINTER(ctypes.c_int),ctypes.POINTER(ctypes.c_int),ctypes.POINTER(ctypes.c_longlong),ctypes.POINTER(ctypes.c_double)]
                lib.cace_p1_1d_stiffness.argtypes=[ctypes.POINTER(ctypes.c_double),ctypes.c_int,ctypes.POINTER(ctypes.c_double),ctypes.POINTER(ctypes.c_int),ctypes.POINTER(ctypes.c_int),ctypes.c_int,ctypes.POINTER(ctypes.c_int),ctypes.POINTER(ctypes.c_int)]
                self.lib=lib
                ver=(lib.cace_runtime_version() or b'').decode()
                return NativeStatus(True,'cpp20-cabi',ver,str(p),'')
            except Exception as e: last=str(e)
        return NativeStatus(False,'python-reference','','',last)

    @staticmethod
    def _f64(a): return np.ascontiguousarray(a,dtype=np.float64)
    @staticmethod
    def _i32(a): return np.ascontiguousarray(a,dtype=np.int32)
    @staticmethod
    def _pd(a): return a.ctypes.data_as(ctypes.POINTER(ctypes.c_double))
    @staticmethod
    def _pi(a): return a.ctypes.data_as(ctypes.POINTER(ctypes.c_int))

    def csr_matvec(self,csr,x):
        if not self.lib: raise RuntimeError(self.status.reason)
        d=self._f64(csr['data']); ix=self._i32(csr['indices']); ip=self._i32(csr['indptr']); xv=self._f64(x)
        n=int(csr['shape'][0]); y=np.zeros(n,dtype=np.float64)
        rc=self.lib.cace_csr_matvec(self._pd(d),self._pi(ix),self._pi(ip),n,len(d),self._pd(xv),len(xv),self._pd(y))
        if rc: raise RuntimeError(f'native csr_matvec failed with code {rc}')
        return y

    def csr_residual_inf(self,csr,x,b):
        if not self.lib: raise RuntimeError(self.status.reason)
        d=self._f64(csr['data']); ix=self._i32(csr['indices']); ip=self._i32(csr['indptr']); xv=self._f64(x); bv=self._f64(b)
        out=ctypes.c_double(); n=int(csr['shape'][0])
        rc=self.lib.cace_csr_residual_inf(self._pd(d),self._pi(ix),self._pi(ip),n,len(d),self._pd(xv),len(xv),self._pd(bv),len(bv),ctypes.byref(out))
        if rc: raise RuntimeError(f'native csr_residual_inf failed with code {rc}')
        return float(out.value)

    def dorfler_mark(self,eta,theta):
        if not self.lib: raise RuntimeError(self.status.reason)
        e=self._f64(eta); out=np.zeros(len(e),dtype=np.int32); nout=ctypes.c_int()
        rc=self.lib.cace_dorfler_mark(self._pd(e),len(e),float(theta),self._pi(out),len(out),ctypes.byref(nout))
        if rc: raise RuntimeError(f'native dorfler_mark failed with code {rc}')
        return out[:nout.value].astype(int).tolist()

    def p1_1d_stiffness(self,nodes):
        if not self.lib: raise RuntimeError(self.status.reason)
        x=self._f64(nodes); cap=max(1,3*max(0,len(x)-2)); data=np.zeros(cap,dtype=np.float64); ix=np.zeros(cap,dtype=np.int32); ip=np.zeros(max(1,len(x)),dtype=np.int32); nnz=ctypes.c_int(); nrows=ctypes.c_int()
        rc=self.lib.cace_p1_1d_stiffness(self._pd(x),len(x),self._pd(data),self._pi(ix),self._pi(ip),cap,ctypes.byref(nnz),ctypes.byref(nrows))
        if rc: raise RuntimeError(f'native p1_1d_stiffness failed with code {rc}')
        return {'shape':[nrows.value,nrows.value],'data':data[:nnz.value].tolist(),'indices':ix[:nnz.value].astype(int).tolist(),'indptr':ip[:nrows.value+1].astype(int).tolist()}

    def sparse_ldlt_stats(self,csr,order):
        if not self.lib: raise RuntimeError(self.status.reason)
        d=self._f64(csr['data']);ix=self._i32(csr['indices']);ip=self._i32(csr['indptr']);ordv=self._i32(order);fn=ctypes.c_int();fill=ctypes.c_int();piv=ctypes.c_double();n=int(csr['shape'][0])
        rc=self.lib.cace_sparse_ldlt_stats(self._pd(d),self._pi(ix),self._pi(ip),n,len(d),self._pi(ordv),len(ordv),ctypes.byref(fn),ctypes.byref(fill),ctypes.byref(piv))
        if rc: raise RuntimeError(f'native sparse_ldlt_stats failed with code {rc}')
        return {'factor_nnz':fn.value,'fill_edges':fill.value,'min_pivot':piv.value}

    def sparse_ldlt_solve(self,csr,order,b):
        if not self.lib: raise RuntimeError(self.status.reason)
        d=self._f64(csr['data']);ix=self._i32(csr['indices']);ip=self._i32(csr['indptr']);ordv=self._i32(order);bv=self._f64(b);n=int(csr['shape'][0]);x=np.zeros(n,dtype=np.float64);fn=ctypes.c_int();fill=ctypes.c_int();piv=ctypes.c_double()
        rc=self.lib.cace_sparse_ldlt_solve(self._pd(d),self._pi(ix),self._pi(ip),n,len(d),self._pi(ordv),len(ordv),self._pd(bv),len(bv),self._pd(x),len(x),ctypes.byref(fn),ctypes.byref(fill),ctypes.byref(piv))
        if rc: raise RuntimeError(f'native sparse_ldlt_solve failed with code {rc}')
        return {'x':x.tolist(),'factor_nnz':fn.value,'fill_edges':fill.value,'min_pivot':piv.value}


    def sparse_multifrontal_ldlt_solve(self,csr,order,b,max_parallel_depth=2):
        if not self.lib: raise RuntimeError(self.status.reason)
        d=self._f64(csr['data']);ix=self._i32(csr['indices']);ip=self._i32(csr['indptr']);ordv=self._i32(order);bv=self._f64(b);n=int(csr['shape'][0]);x=np.zeros(n,dtype=np.float64)
        fn=ctypes.c_int();fill=ctypes.c_int();piv=ctypes.c_double();peak=ctypes.c_int();total=ctypes.c_longlong();tasks=ctypes.c_int();ms=ctypes.c_double()
        rc=self.lib.cace_sparse_multifrontal_ldlt_solve(self._pd(d),self._pi(ix),self._pi(ip),n,len(d),self._pi(ordv),len(ordv),self._pd(bv),len(bv),int(max_parallel_depth),self._pd(x),len(x),ctypes.byref(fn),ctypes.byref(fill),ctypes.byref(piv),ctypes.byref(peak),ctypes.byref(total),ctypes.byref(tasks),ctypes.byref(ms))
        if rc: raise RuntimeError(f'native sparse_multifrontal_ldlt_solve failed with code {rc}')
        return {'x':x.tolist(),'factor_nnz':fn.value,'fill_edges':fill.value,'min_pivot':piv.value,'peak_front_size':peak.value,'total_front_entries':int(total.value),'parallel_tasks':tasks.value,'factor_solve_ms':ms.value}


    def sparse_supernodal_ldlt_solve(self,csr,order,b,threads=0):
        if not self.lib: raise RuntimeError(self.status.reason)
        d=self._f64(csr['data']);ix=self._i32(csr['indices']);ip=self._i32(csr['indptr']);ordv=self._i32(order);bv=self._f64(b);n=int(csr['shape'][0]);x=np.zeros(n,dtype=np.float64)
        fn=ctypes.c_int();fill=ctypes.c_int();piv=ctypes.c_double();sns=ctypes.c_int();maxsn=ctypes.c_int();peak=ctypes.c_int();total=ctypes.c_longlong();flops=ctypes.c_longlong();nth=ctypes.c_int();tasks=ctypes.c_int();reallocs=ctypes.c_int();peakws=ctypes.c_longlong();ms=ctypes.c_double()
        rc=self.lib.cace_sparse_supernodal_ldlt_solve(self._pd(d),self._pi(ix),self._pi(ip),n,len(d),self._pi(ordv),len(ordv),self._pd(bv),len(bv),int(threads),self._pd(x),len(x),ctypes.byref(fn),ctypes.byref(fill),ctypes.byref(piv),ctypes.byref(sns),ctypes.byref(maxsn),ctypes.byref(peak),ctypes.byref(total),ctypes.byref(flops),ctypes.byref(nth),ctypes.byref(tasks),ctypes.byref(reallocs),ctypes.byref(peakws),ctypes.byref(ms))
        if rc: raise RuntimeError(f'native sparse_supernodal_ldlt_solve failed with code {rc}')
        return {'x':x.tolist(),'factor_nnz':fn.value,'fill_edges':fill.value,'min_pivot':piv.value,'supernodes':sns.value,'max_supernode_size':maxsn.value,'peak_front_size':peak.value,'total_front_entries':int(total.value),'block_flop_proxy':int(flops.value),'thread_count':nth.value,'scheduled_tasks':tasks.value,'workspace_reallocations':reallocs.value,'peak_workspace_entries':int(peakws.value),'factor_solve_ms':ms.value}
