"""Type stubs for PIL.Image module."""

from typing import Any, Tuple, Union

class Image:
    """PIL Image class stub."""
    
    size: Tuple[int, int]
    mode: str
    format: str | None
    
    def __init__(self) -> None: ...
    
    def resize(
        self,
        size: Tuple[int, int],
        resample: int = ...,
        box: Tuple[float, float, float, float] | None = ...,
        reducing_gap: float | None = ...
    ) -> Image: ...
    
    def save(
        self,
        fp: str | Any,
        format: str | None = ...,
        **params: Any
    ) -> None: ...
    
    def convert(
        self,
        mode: str | None = ...,
        matrix: Any = ...,
        dither: int | None = ...,
        palette: int = ...,
        colors: int = ...
    ) -> Image: ...

NEAREST: int
BILINEAR: int
BICUBIC: int
LANCZOS: int

def new(
    mode: str,
    size: Tuple[int, int],
    color: Union[int, Tuple[int, ...], str] = ...
) -> Image: ...

def open(fp: str | Any, mode: str = ..., formats: Any = ...) -> Image: ...
