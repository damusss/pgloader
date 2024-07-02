import pygame
import dataclasses


__all__ = (
    "MetaError",
    "settings",
    "default_settings",
    "sheet_settings",
    "children_settings",
    "pygame",
)


class MetaError(RuntimeError): ...


class _MetaStorage:
    def __init__(self):
        self.reset()

    def validate(self, type_):
        if type_ == "folder" and self.name == "sheet_settings":
            raise MetaError("Folder meta cannot call meta.sheet_settings")
        if type_ == "asset" and self.name == "children_settings":
            raise MetaError("Asset meta cannot call meta.children_settings")

    def reset(self):
        self.name = None
        self.settings = None
        self.default_settings = None
        self.children_settings = None
        self.sheet_settings = None


__META_STORAGE__ = _MetaStorage()


@dataclasses.dataclass
class _MetaSettings:
    alpha: bool = None
    size: tuple[int, int] = None
    scale: float | tuple[float, float] = None
    unit_size: tuple[float, float] = None
    colorkey: str | list[int] | int | pygame.Color = None
    global_alpha: int = None
    smoothscale: bool = None

    def apply_default(self, s: "_MetaSettings"):
        for attrname in [
            "alpha",
            "size",
            "scale",
            "unit_size",
            "colorkey",
            "global_alpha",
            "smoothscale",
        ]:
            if getattr(self, attrname) is None and getattr(s, attrname) is not None:
                setattr(self, attrname, getattr(s, attrname))
        return self

    def copy(self):
        return _MetaSettings(
            self.alpha,
            self.size,
            self.scale,
            self.unit_size,
            self.colorkey,
            self.global_alpha,
            self.smoothscale,
        )


@dataclasses.dataclass
class _SheetMetaSettings:
    rows: int
    columns: int
    padding: int = 0
    coordinate_settings: dict[tuple[int], _MetaSettings] = None


@dataclasses.dataclass
class _ChildrenMetaSettings:
    settings: dict[str | tuple[str], _MetaSettings] = None


def _store(name, data):
    if getattr(__META_STORAGE__, name) is not None:
        return
    __META_STORAGE__.name = name
    setattr(__META_STORAGE__, name, data)


def settings(
    *,
    alpha: bool = None,
    size: tuple[int, int] = None,
    scale: float | tuple[float, float] = None,
    unit_size: tuple[float, float] = None,
    colorkey: str | list[int] | int | pygame.Color = None,
    global_alpha: int = None,
    smoothscale: bool = None,
):
    s = _MetaSettings(
        alpha, size, scale, unit_size, colorkey, global_alpha, smoothscale
    )
    _store("settings", s)
    return s


def default_settings(
    *,
    alpha: bool = None,
    size: tuple[int, int] = None,
    scale: float | tuple[float, float] = None,
    unit_size: tuple[float, float] = None,
    colorkey: str | list[int] | int | pygame.Color = None,
    global_alpha: int = None,
    smoothscale: bool = None,
):
    s = _MetaSettings(
        alpha, size, scale, unit_size, colorkey, global_alpha, smoothscale
    )
    _store("default_settings", s)
    return s


def sheet_settings(
    *,
    rows: int,
    columns: int,
    padding: int = 0,
    coordinate_settings: dict[tuple[int], _MetaSettings] = None,
):
    if not isinstance(rows, int) or not isinstance(columns, int):
        raise MetaError("sheet_settings rows and columns must be integers")
    if rows < 1 or columns < 1:
        raise MetaError("sheet_settings rows and colums must be >= 1")
    if coordinate_settings is None:
        coordinate_settings = {}
    for pos, cs in coordinate_settings.items():
        if not isinstance(pos, tuple):
            raise MetaError(
                f"every coordinate in sheet_settings must be a tuple of numbers, not {type(pos)}"
            )
        if not isinstance(cs, _MetaSettings):
            raise MetaError(
                f"every settings in sheet_settings must be the result of meta.settings, not {type(cs)}"
            )
    s = _SheetMetaSettings(rows, columns, int(padding), coordinate_settings)
    _store("sheet_settings", s)
    return s


def children_settings(name_settings: dict[str | tuple[str], _MetaSettings]):
    for name, s in name_settings.items():
        if not isinstance(name, (str, tuple)):
            raise MetaError(
                f"every name in children_settings must be a string or a tuple of strings, not {type(name)}"
            )
        if not isinstance(s, _MetaSettings):
            raise MetaError(
                f"every settings in children_settings must be the result of meta.settings, not {type(s)}"
            )

    cs = _ChildrenMetaSettings(name_settings)
    _store("children_settings", cs)
    return cs
