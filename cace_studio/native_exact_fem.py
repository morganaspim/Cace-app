from __future__ import annotations

import ctypes
from fractions import Fraction
import re
from typing import Any

import numpy as np

from cace_studio.core.native_runtime import NativeRuntime


_EXACT_RATIONAL_TEXT = re.compile(r"^[+-]?\d+(?:/[+-]?\d+)?$")
_INT64 = np.iinfo(np.int64)
_INT32 = np.iinfo(np.int32)


class ExactFemNativeRuntime:
    """Thin orchestration wrapper for CACE's C++ exact-FEM kernel.

    This module intentionally contains no FEM mathematics. Python validates and
    marshals exact representations, invokes the C ABI, and packages the exact
    native results. The scientific semantics remain in C++ and formal proof
    remains a separate Lean qualification gate.
    """

    def __init__(self, base_runtime: NativeRuntime | None = None):
        self.base = base_runtime or NativeRuntime()
        self.lib = self.base.lib
        self.status = self.base.status
        self.exact_available = bool(
            self.lib is not None and hasattr(self.lib, "cace_exact_mesh_create")
        )
        if self.exact_available:
            self._configure_exact_api()

    def _configure_exact_api(self) -> None:
        assert self.lib is not None
        self.lib.cace_exact_mesh_create.argtypes = [
            ctypes.POINTER(ctypes.c_int64),
            ctypes.POINTER(ctypes.c_int64),
            ctypes.c_int,
            ctypes.POINTER(ctypes.c_int),
            ctypes.c_int,
        ]
        self.lib.cace_exact_mesh_create.restype = ctypes.c_void_p
        self.lib.cace_exact_mesh_destroy.argtypes = [ctypes.c_void_p]
        self.lib.cace_exact_mesh_counts.argtypes = [
            ctypes.c_void_p,
            ctypes.POINTER(ctypes.c_int),
            ctypes.POINTER(ctypes.c_int),
            ctypes.POINTER(ctypes.c_int),
            ctypes.POINTER(ctypes.c_int),
            ctypes.POINTER(ctypes.c_int),
        ]
        self.lib.cace_exact_mesh_signed_jacobian.argtypes = [
            ctypes.c_void_p,
            ctypes.c_int,
            ctypes.POINTER(ctypes.c_int64),
            ctypes.POINTER(ctypes.c_int64),
        ]
        self.lib.cace_exact_assembly_status.argtypes = [
            ctypes.c_void_p,
            ctypes.POINTER(ctypes.c_int64),
            ctypes.POINTER(ctypes.c_int64),
            ctypes.POINTER(ctypes.c_int64),
            ctypes.POINTER(ctypes.c_int64),
            ctypes.c_int,
            ctypes.POINTER(ctypes.c_int),
            ctypes.POINTER(ctypes.c_int),
            ctypes.POINTER(ctypes.c_int),
            ctypes.POINTER(ctypes.c_int),
            ctypes.POINTER(ctypes.c_int),
            ctypes.POINTER(ctypes.c_int),
        ]
        self.lib.cace_exact_cell_values.argtypes = [
            ctypes.c_void_p,
            ctypes.POINTER(ctypes.c_int64),
            ctypes.POINTER(ctypes.c_int64),
            ctypes.POINTER(ctypes.c_int64),
            ctypes.POINTER(ctypes.c_int64),
            ctypes.c_int,
            ctypes.POINTER(ctypes.c_int64),
            ctypes.POINTER(ctypes.c_int64),
            ctypes.c_int,
        ]

    @staticmethod
    def _exact_fraction(value: Any) -> Fraction:
        if isinstance(value, bool) or isinstance(value, float):
            raise ValueError(
                "exact native inputs must not be booleans or binary floats"
            )
        if isinstance(value, Fraction):
            return value
        if isinstance(value, int):
            return Fraction(value, 1)
        if isinstance(value, str):
            if not _EXACT_RATIONAL_TEXT.fullmatch(value):
                raise ValueError(
                    "exact rational strings must use integer or numerator/denominator form"
                )
            try:
                return Fraction(value)
            except (ValueError, ZeroDivisionError) as exc:
                raise ValueError(f"invalid exact rational {value!r}") from exc
        raise TypeError(
            f"unsupported exact rational input type: {type(value).__name__}"
        )

    @classmethod
    def _exact_arrays(cls, values):
        fractions = [cls._exact_fraction(value) for value in values]
        for value in fractions:
            if not (_INT64.min <= value.numerator <= _INT64.max):
                raise OverflowError("exact rational numerator exceeds int64 ABI range")
            if not (1 <= value.denominator <= _INT64.max):
                raise OverflowError("exact rational denominator exceeds int64 ABI range")
        nums = np.ascontiguousarray(
            [value.numerator for value in fractions], dtype=np.int64
        )
        dens = np.ascontiguousarray(
            [value.denominator for value in fractions], dtype=np.int64
        )
        return nums, dens

    @staticmethod
    def _pi(values):
        return values.ctypes.data_as(ctypes.POINTER(ctypes.c_int))

    @staticmethod
    def _pi64(values):
        return values.ctypes.data_as(ctypes.POINTER(ctypes.c_int64))

    def exact_fem_evaluate(self, vertices, triangles, p1_cells, rt0_cells):
        if self.lib is None:
            raise RuntimeError(self.status.reason)
        if not self.exact_available:
            raise RuntimeError("native library predates exact-FEM C ABI")
        if len(vertices) < 3:
            raise ValueError("exact mesh requires at least three vertices")
        if not triangles:
            raise ValueError("exact mesh requires at least one triangle")
        if len(p1_cells) != len(triangles) or len(rt0_cells) != len(triangles):
            raise ValueError(
                "P1/RT0 arrays must have exactly one entry per triangle"
            )

        coordinate_values = []
        for vertex in vertices:
            if len(vertex) != 2:
                raise ValueError("each exact vertex requires x,y")
            coordinate_values.extend(vertex)
        coord_num, coord_den = self._exact_arrays(coordinate_values)

        strict_triangles = []
        for triangle in triangles:
            if len(triangle) != 3:
                raise ValueError("triangles must be an N x 3 integer array")
            row = []
            for vertex_id in triangle:
                if isinstance(vertex_id, bool) or not isinstance(vertex_id, int):
                    raise ValueError("triangle vertex ids must be genuine integers")
                if vertex_id < 0 or vertex_id > _INT32.max:
                    raise ValueError(
                        "triangle vertex ids must fit nonnegative int32"
                    )
                row.append(vertex_id)
            strict_triangles.append(row)
        tri = np.ascontiguousarray(strict_triangles, dtype=np.int32)

        def flatten_cells(cells, name):
            values = []
            for cell in cells:
                if len(cell) != 3:
                    raise ValueError(
                        f"{name} cells require exactly three coefficients"
                    )
                values.extend(cell)
            return self._exact_arrays(values)

        pnum, pden = flatten_cells(p1_cells, "P1")
        qnum, qden = flatten_cells(rt0_cells, "RT0")

        handle = self.lib.cace_exact_mesh_create(
            self._pi64(coord_num),
            self._pi64(coord_den),
            len(vertices),
            self._pi(tri.reshape(-1)),
            len(triangles),
        )
        if not handle:
            raise RuntimeError("native exact mesh construction failed")

        try:
            nv = ctypes.c_int()
            nt = ctypes.c_int()
            ne = ctypes.c_int()
            ni = ctypes.c_int()
            nb = ctypes.c_int()
            rc = self.lib.cace_exact_mesh_counts(
                handle,
                ctypes.byref(nv),
                ctypes.byref(nt),
                ctypes.byref(ne),
                ctypes.byref(ni),
                ctypes.byref(nb),
            )
            if rc:
                raise RuntimeError(
                    f"native exact mesh counts failed with code {rc}"
                )

            jacobians = []
            for cell in range(len(triangles)):
                num = ctypes.c_int64()
                den = ctypes.c_int64()
                rc = self.lib.cace_exact_mesh_signed_jacobian(
                    handle, cell, ctypes.byref(num), ctypes.byref(den)
                )
                if rc:
                    raise RuntimeError(
                        f"native exact Jacobian failed with code {rc}"
                    )
                jacobians.append(str(Fraction(num.value, den.value)))

            ready = ctypes.c_int()
            local_green = ctypes.c_int()
            orthogonality = ctypes.c_int()
            eq_fail = ctypes.c_int()
            bdy_fail = ctypes.c_int()
            int_fail = ctypes.c_int()
            rc = self.lib.cace_exact_assembly_status(
                handle,
                self._pi64(pnum),
                self._pi64(pden),
                self._pi64(qnum),
                self._pi64(qden),
                len(triangles),
                ctypes.byref(ready),
                ctypes.byref(local_green),
                ctypes.byref(orthogonality),
                ctypes.byref(eq_fail),
                ctypes.byref(bdy_fail),
                ctypes.byref(int_fail),
            )
            if rc:
                raise RuntimeError(
                    f"native exact assembly status failed with code {rc}"
                )

            cell_values = []
            for cell in range(len(triangles)):
                nums = np.zeros(5, dtype=np.int64)
                dens = np.zeros(5, dtype=np.int64)
                rc = self.lib.cace_exact_cell_values(
                    handle,
                    self._pi64(pnum),
                    self._pi64(pden),
                    self._pi64(qnum),
                    self._pi64(qden),
                    cell,
                    self._pi64(nums),
                    self._pi64(dens),
                    5,
                )
                if rc:
                    raise RuntimeError(
                        f"native exact cell evaluation failed with code {rc}"
                    )
                values = [
                    str(Fraction(int(nums[i]), int(dens[i])))
                    for i in range(5)
                ]
                cell_values.append(
                    {
                        "cell_pairing": values[0],
                        "cell_divergence": values[1],
                        "local_face_pairings": values[2:],
                    }
                )

            return {
                "backend": "cpp20-cabi-exact-fem",
                "native_version": self.status.version,
                "counts": {
                    "vertices": nv.value,
                    "triangles": nt.value,
                    "edges": ne.value,
                    "interior_edges": ni.value,
                    "boundary_edges": nb.value,
                },
                "signed_jacobians": jacobians,
                "cell_values": cell_values,
                "assembly": {
                    "all_local_green": bool(local_green.value),
                    "orthogonality_sum_zero": bool(orthogonality.value),
                    "equilibrium_failures": eq_fail.value,
                    "boundary_failures": bdy_fail.value,
                    "interior_failures": int_fail.value,
                    "ready_for_lean_assembly": bool(ready.value),
                },
                "formal_state": "generated-inputs-unqualified",
                "scope_note": (
                    "Exact C++ runtime evidence only. Lean theorem instantiation "
                    "and canonical qualification are separate required gates."
                ),
            }
        finally:
            self.lib.cace_exact_mesh_destroy(handle)
