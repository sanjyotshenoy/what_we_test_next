"""CPU or GPU for the graph code: plain pandas + networkx, or the same code accelerated by RAPIDS.

    python -m kg.query templates P10721              # CPU (default; no GPU packages needed)
    WWTN_GPU=1 python -m kg.query templates P10721   # GPU: cudf.pandas + the nx-cugraph backend

GPU mode needs `pip install -r requirements-gpu.txt` and a visible NVIDIA GPU. It is switched on when the `kg`
package is first imported, so WWTN_GPU must be set in the environment before Python starts: cudf.pandas only
accelerates pandas if it is installed before pandas is imported, and nx-cugraph registers itself as networkx's
preferred backend only if NX_CUGRAPH_AUTOCONFIG is set before networkx is imported. The code itself is identical in
both modes; anything RAPIDS can't run on the GPU falls back to the CPU transparently.
"""
import os
import sys
import tempfile
from typing import Mapping

TRUE = {"1", "true", "yes", "on", "gpu"}
_mode = "cpu"


def wants_gpu(env: Mapping[str, str] = os.environ) -> bool:
    return (env.get("WWTN_GPU") or "").strip().lower() in TRUE


def mode() -> str:
    """'gpu' if RAPIDS acceleration is active in this process, else 'cpu'."""
    return _mode


def activate_from_env() -> str:
    global _mode
    if _mode == "gpu" or not wants_gpu():
        return _mode
    already = [m for m in ("pandas", "networkx") if m in sys.modules]
    if already:
        raise RuntimeError(f"WWTN_GPU is set, but {' and '.join(already)} was imported first: GPU mode has to be "
                           "chosen before pandas or networkx is imported (set WWTN_GPU=1 when starting Python)")
    os.environ.setdefault("CUPY_CACHE_DIR", os.path.join(tempfile.gettempdir(), "cupy"))
    os.environ.setdefault("NX_CUGRAPH_AUTOCONFIG", "True")
    import cudf.pandas
    cudf.pandas.install()
    _mode = "gpu"
    return _mode


def gpu_available() -> bool:
    """True if the RAPIDS packages import and CUDA sees at least one device."""
    os.environ.setdefault("CUPY_CACHE_DIR", os.path.join(tempfile.gettempdir(), "cupy"))
    try:
        import cupy
        return cupy.cuda.runtime.getDeviceCount() > 0
    except Exception:  # noqa: BLE001 - no package, no driver, or no device all mean "no"
        return False
