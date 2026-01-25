#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Minimal OpenCL device lister (no extra deps).

This helps configure BaramFlow's external OpenCL backend.

Notes:
- OpenCL device aggregation (CPU+iGPU+dGPU simultaneously) must be implemented
  by the external solver itself (e.g., FluidX3D-like). This tool only lists
  devices so you can choose a multi-device selection string.
"""

from __future__ import annotations

import ctypes
import ctypes.wintypes
import platform


CL_SUCCESS = 0
CL_PLATFORM_NAME = 0x0902
CL_PLATFORM_VENDOR = 0x0903
CL_PLATFORM_VERSION = 0x0901

CL_DEVICE_NAME = 0x102B
CL_DEVICE_VENDOR = 0x102C
CL_DEVICE_VERSION = 0x102F
CL_DEVICE_TYPE = 0x1000

CL_DEVICE_TYPE_CPU = 1 << 1
CL_DEVICE_TYPE_GPU = 1 << 2


def _load_opencl():
    system = platform.system()
    if system == 'Windows':
        return ctypes.WinDLL('OpenCL.dll')
    if system == 'Darwin':
        return ctypes.CDLL('/System/Library/Frameworks/OpenCL.framework/OpenCL')
    return ctypes.CDLL('libOpenCL.so')


def _get_info_string(fn, handle, param_name: int) -> str:
    size = ctypes.c_size_t(0)
    rc = fn(handle, param_name, 0, None, ctypes.byref(size))
    if rc != CL_SUCCESS or size.value == 0:
        return ''
    buf = (ctypes.c_char * size.value)()
    rc = fn(handle, param_name, size.value, buf, None)
    if rc != CL_SUCCESS:
        return ''
    return ctypes.string_at(buf).decode(errors='replace').rstrip('\x00')


def _device_type_to_str(device_type: int) -> str:
    parts: list[str] = []
    if device_type & CL_DEVICE_TYPE_CPU:
        parts.append('CPU')
    if device_type & CL_DEVICE_TYPE_GPU:
        parts.append('GPU')
    return '+'.join(parts) if parts else hex(device_type)


def main() -> int:
    try:
        cl = _load_opencl()
    except Exception as e:
        print(f'OpenCL not available: {e}')
        return 1

    # Signatures
    cl.clGetPlatformIDs.argtypes = [ctypes.c_uint, ctypes.POINTER(ctypes.c_void_p), ctypes.POINTER(ctypes.c_uint)]
    cl.clGetPlatformIDs.restype = ctypes.c_int

    cl.clGetPlatformInfo.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_size_t, ctypes.c_void_p, ctypes.POINTER(ctypes.c_size_t)]
    cl.clGetPlatformInfo.restype = ctypes.c_int

    cl.clGetDeviceIDs.argtypes = [ctypes.c_void_p, ctypes.c_ulong, ctypes.c_uint, ctypes.POINTER(ctypes.c_void_p), ctypes.POINTER(ctypes.c_uint)]
    cl.clGetDeviceIDs.restype = ctypes.c_int

    cl.clGetDeviceInfo.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_size_t, ctypes.c_void_p, ctypes.POINTER(ctypes.c_size_t)]
    cl.clGetDeviceInfo.restype = ctypes.c_int

    num_platforms = ctypes.c_uint(0)
    rc = cl.clGetPlatformIDs(0, None, ctypes.byref(num_platforms))
    if rc != CL_SUCCESS or num_platforms.value == 0:
        print('No OpenCL platforms found.')
        return 2

    platforms = (ctypes.c_void_p * num_platforms.value)()
    rc = cl.clGetPlatformIDs(num_platforms.value, platforms, None)
    if rc != CL_SUCCESS:
        print(f'clGetPlatformIDs failed: {rc}')
        return 3

    print(f'Platforms: {num_platforms.value}')
    global_device_index = 0

    for pi, platform_handle in enumerate(platforms):
        pname = _get_info_string(cl.clGetPlatformInfo, platform_handle, CL_PLATFORM_NAME)
        pvendor = _get_info_string(cl.clGetPlatformInfo, platform_handle, CL_PLATFORM_VENDOR)
        pver = _get_info_string(cl.clGetPlatformInfo, platform_handle, CL_PLATFORM_VERSION)
        print(f'[{pi}] {pname} | {pvendor} | {pver}')

        num_devices = ctypes.c_uint(0)
        rc = cl.clGetDeviceIDs(platform_handle, 0xFFFFFFFFFFFFFFFF, 0, None, ctypes.byref(num_devices))
        if rc != CL_SUCCESS or num_devices.value == 0:
            print('    (no devices)')
            continue

        devices = (ctypes.c_void_p * num_devices.value)()
        rc = cl.clGetDeviceIDs(platform_handle, 0xFFFFFFFFFFFFFFFF, num_devices.value, devices, None)
        if rc != CL_SUCCESS:
            print(f'    clGetDeviceIDs failed: {rc}')
            continue

        for di, device_handle in enumerate(devices):
            dname = _get_info_string(cl.clGetDeviceInfo, device_handle, CL_DEVICE_NAME)
            dvendor = _get_info_string(cl.clGetDeviceInfo, device_handle, CL_DEVICE_VENDOR)
            dver = _get_info_string(cl.clGetDeviceInfo, device_handle, CL_DEVICE_VERSION)

            dtype = ctypes.c_ulong(0)
            size = ctypes.c_size_t(ctypes.sizeof(dtype))
            rc = cl.clGetDeviceInfo(device_handle, CL_DEVICE_TYPE, size.value, ctypes.byref(dtype), None)
            dtype_str = _device_type_to_str(int(dtype.value)) if rc == CL_SUCCESS else 'unknown'

            print(f'    dev[{di}] global={global_device_index}: {dname} | {dvendor} | {dver} | {dtype_str}')
            global_device_index += 1

    print('\nSuggested config examples:')
    print('  solver_env:')
    print("    BARAM_OPENCL_DEVICES: '0,1,2'   # external solver must support multi-device")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
