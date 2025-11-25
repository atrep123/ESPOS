"""Type stubs for PIL.ImageDraw module."""

from typing import Any, Sequence, Tuple, Union

ColorType = Union[str, Tuple[int, int, int], Tuple[int, int, int, int]]
XYType = Sequence[Union[int, float]]

class ImageDraw:
    """Drawing interface for PIL images."""
    
    def __init__(self, im: Any, mode: str = ...) -> None: ...
    
    def rectangle(
        self,
        xy: Union[Sequence[XYType], Sequence[float]],
        fill: ColorType = ...,
        outline: ColorType = ...,
        width: int = ...
    ) -> None: ...
    
    def line(
        self,
        xy: Union[Sequence[XYType], Sequence[float]],
        fill: ColorType = ...,
        width: int = ...,
        joint: str = ...
    ) -> None: ...
    
    def ellipse(
        self,
        xy: Union[Sequence[XYType], Sequence[float]],
        fill: ColorType = ...,
        outline: ColorType = ...,
        width: int = ...
    ) -> None: ...
    
    def text(
        self,
        xy: XYType,
        text: str,
        fill: ColorType = ...,
        font: Any = ...,
        anchor: str = ...,
        spacing: int = ...,
        align: str = ...,
        direction: str = ...,
        features: Any = ...,
        language: str = ...,
        stroke_width: int = ...,
        stroke_fill: ColorType = ...,
        embedded_color: bool = ...
    ) -> None: ...

def Draw(im: Any, mode: str = ...) -> ImageDraw: ...
