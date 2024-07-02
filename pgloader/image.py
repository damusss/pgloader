import pygame
import os
import string
import warnings
import typing
from . import meta as pgloadermeta

__all__ = (
    "LoadError",
    "Image",
    "register_refresh",
    "get",
    "gets",
    "get_from",
    "get_all",
    "get_sheet",
    "exists",
    "exists_folder",
    "exists_sheet",
    "sheet_has",
    "set_unit",
    "get_unit",
    "load",
    "reload",
    "refresh",
    "default_settings",
    "pygame",
)


class LoadError(RuntimeError): ...


class _ctx:
    unit = None
    load_folder = None
    folders = []
    images = {}
    folder_images = {}
    sheets = {}
    default_settings = None
    refresh_callbacks = []

    FOLDER_META_FILENAME = "folder_meta.py"
    FOLDER_PARENT_FILENAME = "folder_parent.meta"
    REGISTER_PARENT_FILENAME = "register_parent.meta"
    SUPPORTED_FORMATS = [
        "png",
        "jpg",
        "jpeg",
        "gif",
        "bmp",
        "lbm",
        "pbm",
        "pgm",
        "ppm",
        "pcx",
        "pnm",
        "svg",
        "tga",
        "tiff",
        "webp",
        "xpm",
    ]

    @staticmethod
    def validate_parent_id(ID):
        ALLOWED_CHARS = string.ascii_letters + string.digits + "._-"
        for char in ID:
            if char not in ALLOWED_CHARS:
                raise LoadError(
                    f"Illegal character in parent ID '{char}', allowed characters are '{ALLOWED_CHARS}'"
                )

    @staticmethod
    def read_file(path):
        with open(path, "r") as file:
            return file.read()

    class AssetMetaPair:
        def __init__(self, asset_path, asset_name, folder_name, has_meta):
            self.asset_path, self.asset_name, self.folder_name, self.has_meta = (
                asset_path,
                asset_name,
                folder_name,
                has_meta,
            )

        def get_raw_surface(self, settings: pgloadermeta._MetaSettings):
            alpha = settings.alpha if settings.alpha is not None else True
            img = pygame.image.load(self.asset_path)
            raw_surface = img.convert_alpha() if alpha else img.convert()
            return raw_surface

        def get_scale_funcs(self, settings: pgloadermeta._MetaSettings):
            smooth = settings.smoothscale if settings.smoothscale is not None else False
            return (
                (pygame.transform.smoothscale if smooth else pygame.transform.scale),
                (
                    pygame.transform.smoothscale_by
                    if smooth
                    else pygame.transform.scale_by
                ),
            )

        def get_image(
            self,
            settings: pgloadermeta._MetaSettings,
            image,
        ):
            scale, scaleby = self.get_scale_funcs(settings)
            if settings.size is not None:
                image = scale(image, (int(settings.size[0]), int(settings.size[1])))
            if settings.scale is not None:
                image = scaleby(image, settings.scale)
            if settings.unit_size is not None:
                w, h = (
                    _ctx.unit * settings.unit_size[0],
                    _ctx.unit * settings.unit_size[1],
                )
                image = scale(image, (int(w), int(h)))

            if settings.global_alpha is not None:
                image.set_alpha(settings.global_alpha)
            if settings.colorkey is not None:
                image.set_colorkey(settings.colorkey)
            return image

        def load(self, settings: pgloadermeta._MetaSettings):
            raw_surface = self.get_raw_surface(settings)
            image = self.get_image(settings, raw_surface.copy())
            name = f"{self.folder_name}/{self.asset_name}"
            if name in _ctx.images:
                _ctx.images[name].__refresh__(raw_surface, image, settings)
            else:
                _ctx.images[name] = Image().__refresh__(raw_surface, image, settings)

        def load_sheet(
            self,
            settings: pgloadermeta._MetaSettings,
            sheet_settings: pgloadermeta._SheetMetaSettings,
        ):
            raw_surface = self.get_raw_surface(settings)
            main_name = f"{self.folder_name}/{self.asset_name}"
            if (
                sheet_settings.rows > raw_surface.width
                or sheet_settings.columns > raw_surface.height
            ):
                raise LoadError(
                    f"Sheet '{main_name}' layout has too many rows or columns compared to pixels"
                )
            sheet_pos = []
            width, height = (
                raw_surface.width // sheet_settings.columns,
                raw_surface.height // sheet_settings.rows,
            )
            raw_rect = raw_surface.get_rect()

            for r in range(sheet_settings.rows):
                for c in range(sheet_settings.columns):
                    subsurface_rect = pygame.Rect(
                        c * width + sheet_settings.padding * c,
                        r * height + sheet_settings.padding * height,
                        width,
                        height,
                    )
                    subsurface_rect = subsurface_rect.clip(raw_rect)
                    if subsurface_rect.w == 0 or subsurface_rect.h == 0:
                        subsurface_rect = pygame.Rect(0, 0, 1, 1)
                    raw_subsurface = raw_surface.subsurface(subsurface_rect)
                    pos = (c, r)
                    this_settings = settings
                    if pos in sheet_settings.coordinate_settings:
                        this_settings = sheet_settings.coordinate_settings[pos]
                    image = self.get_image(this_settings, raw_subsurface)
                    this_name = f"{main_name}({c},{r})"
                    if this_name in _ctx.images:
                        _ctx.images[this_name].__refresh__(
                            raw_subsurface, image, this_settings
                        )
                    else:
                        _ctx.images[this_name] = Image().__refresh__(
                            raw_subsurface, image, this_settings
                        )
                    sheet_pos.append(pos)

            _ctx.sheets[main_name] = sheet_pos

        def __str__(self):
            return f"Asset(path={self.asset_path}, name={self.asset_name}, folder={self.folder_name}{", has meta" if self.has_meta else ""})"

        __repr__ = __str__

    class FolderMeta:
        def __init__(self, folder_path, has_meta, asset_pairs):
            self.folder_path, self.has_meta, self.asset_pairs = (
                folder_path,
                has_meta,
                asset_pairs,
            )
            self.folder_name = self.folder_path.split("/")[-1]

        def load(self):
            if _ctx.default_settings is not None:
                default_settings = _ctx.default_settings.copy()
            else:
                default_settings = pgloadermeta._MetaSettings()
            children_settings = {}
            if self.has_meta:
                content = _ctx.read_file(
                    f"{self.folder_path}/{_ctx.FOLDER_META_FILENAME}"
                )
                exec(content)
                pgloadermeta.__META_STORAGE__.validate("folder")
                if pgloadermeta.__META_STORAGE__.settings is not None:
                    default_settings = pgloadermeta.__META_STORAGE__.settings
                if pgloadermeta.__META_STORAGE__.default_settings is not None:
                    default_settings = pgloadermeta.__META_STORAGE__.default_settings
                if pgloadermeta.__META_STORAGE__.children_settings is not None:
                    for (
                        cname,
                        cs,
                    ) in (
                        pgloadermeta.__META_STORAGE__.children_settings.settings.items()
                    ):
                        apply_to = []
                        if isinstance(cname, str):
                            apply_to = [cname]
                        else:
                            apply_to = list(cname)
                        for n in apply_to:
                            children_settings[n] = cs
                pgloadermeta.__META_STORAGE__.reset()
            to_use_children_settings = list(children_settings.keys())
            _ctx.folder_images[self.folder_name] = []
            for asset in self.asset_pairs:
                child_settings: pgloadermeta._MetaSettings = children_settings.get(
                    asset.asset_name, None
                )
                current_settings = default_settings
                if child_settings is not None:
                    to_use_children_settings.remove(asset.asset_name)
                    child_settings.apply_default(default_settings)
                    current_settings = child_settings
                sheet_settings = None
                if asset.has_meta:
                    content = _ctx.read_file(
                        f"{self.folder_path}/{asset.asset_name}_meta.py"
                    )
                    exec(content)
                    pgloadermeta.__META_STORAGE__.validate("asset")
                    if (
                        pgloadermeta.__META_STORAGE__.settings is None
                        and pgloadermeta.__META_STORAGE__.sheet_settings is None
                        and pgloadermeta.__META_STORAGE__.default_settings is None
                    ):
                        raise pgloadermeta.MetaError(
                            f"Asset meta ({self.folder_path}) should call meta.settings/meta.default_settings or meta.sheet_settings or both"
                        )
                    if (
                        pgloadermeta.__META_STORAGE__.settings is not None
                        and pgloadermeta.__META_STORAGE__.default_settings is None
                    ):
                        pgloadermeta.__META_STORAGE__.settings.apply_default(
                            current_settings
                        )
                        current_settings = pgloadermeta.__META_STORAGE__.settings
                    if pgloadermeta.__META_STORAGE__.default_settings is not None:
                        pgloadermeta.__META_STORAGE__.default_settings.apply_default(
                            current_settings
                        )
                        current_settings = (
                            pgloadermeta.__META_STORAGE__.default_settings
                        )
                    if pgloadermeta.__META_STORAGE__.sheet_settings is not None:
                        sheet_settings = pgloadermeta.__META_STORAGE__.sheet_settings
                        sheet_settings.coordinate_settings = {
                            pos: s.apply_default(current_settings)
                            for pos, s in sheet_settings.coordinate_settings.items()
                        }
                    pgloadermeta.__META_STORAGE__.reset()
                if sheet_settings is None:
                    asset.load(current_settings)
                else:
                    asset.load_sheet(current_settings, sheet_settings)
                _ctx.folder_images[self.folder_name].append(asset.asset_name)
            for name in to_use_children_settings:
                warnings.warn(
                    f"Children settings in '{self.folder_path}' specifies settings for the asset '{name}' which does not exist"
                )

        def add_pairs(self, asset_pairs):
            self.asset_pairs.extend(asset_pairs)

        def __str__(self):
            res = (
                f"Folder(path={self.folder_path}, name={self.folder_name}{", has meta" if self.has_meta else ""})"
                + "{\n"
            )
            for asset in self.asset_pairs:
                res += f"\t{str(asset)}\n"
            res += "}"
            return res


class Image:
    def __refresh__(self, raw_surface, image, load_settings):
        self.raw_surface: pygame.Surface = raw_surface
        self.image: pygame.Surface = image
        self.load_settings: pgloadermeta._MetaSettings = load_settings
        self.rect: pygame.Rect = self.image.get_rect()
        self.frect: pygame.FRect = self.image.get_frect()
        self.width: int = self.image.width
        self.height: int = self.image.height
        self.size: tuple[int, int] = self.image.size
        return self


def register_refresh(callback: typing.Callable):
    _ctx.refresh_callbacks.append(callback)


def get(name: str, default=RuntimeError) -> Image:
    if name in _ctx.images:
        return _ctx.images[name]
    if isinstance(default, type) and issubclass(default, Exception):
        raise default(f"Image '{name}' does not exist")
    return default


def gets(*names: str, default=RuntimeError) -> list[Image]:
    return [get(name, default) for name in names]


def get_from(folder: str, *names: str, default=RuntimeError) -> list[Image]:
    return [get(f"{folder}/{name}", default) for name in names]


def get_all(folder: str, default=RuntimeError) -> list[Image]:
    if folder in _ctx.folder_images:
        return [get(f"{folder}/{name}", default) for name in _ctx.folder_images[folder]]
    if isinstance(default, type) and issubclass(default, Exception):
        raise default(f"Folder '{folder}' does not exist")
    return default


def get_sheet(name: str, default=RuntimeError) -> dict[tuple[int, int], Image]:
    if name in _ctx.sheets:
        return {
            pos: get(f"{name}({pos[0]},{pos[1]})", default) for pos in _ctx.sheets[name]
        }
    if isinstance(default, type) and issubclass(default, Exception):
        raise default(f"Sheet '{name}' does not exist")
    return default


def exists(*names: str) -> bool:
    return all([name in _ctx.images for name in names])


def exists_folder(*folders: str) -> bool:
    return all([name in _ctx.folder_images for name in folders])


def exists_sheet(*sheets: str) -> bool:
    return all([name in _ctx.sheets for name in sheets])


def sheet_has(sheet: str, *coordinates: tuple[int, int]):
    return exists_sheet(sheet) and all(
        [exists(f"{sheet}({c[0]},{c[1]})") for c in coordinates]
    )


def set_unit(unit: float):
    unit = float(unit)
    _ctx.unit = unit


def get_unit() -> float:
    if _ctx.unit is None:
        raise LoadError("Unit was not set")
    return _ctx.unit


def default_settings(
    alpha: bool = None,
    size: tuple[int, int] = None,
    scale: float | tuple[float, float] = None,
    unit_size: tuple[float, float] = None,
    colorkey: str | list[int] | int | pygame.Color = None,
    global_alpha: int = None,
    smoothscale: bool = None,
):
    _ctx.default_settings = pgloadermeta._MetaSettings(
        alpha, size, scale, unit_size, colorkey, global_alpha, smoothscale
    )


def load(folder: str, unit: float = None):
    if unit is not None:
        set_unit(unit)
    if _ctx.unit is None:
        raise LoadError("Unit was not set")
    if not os.path.exists(folder):
        raise LoadError("Folder does not exist")
    _ctx.load_folder = folder
    pgloadermeta.__META_STORAGE__.reset()

    parent_folders = {}
    pending_folders = []
    for dir_path, dir_subfolders, dir_files in os.walk(_ctx.load_folder):
        dir_path = dir_path.replace("\\", "/")
        asset_pairs = []
        has_meta = False
        registered_id = None
        parent_id = None
        folder_name = dir_path.split("/")[-1]
        if any([name.endswith("_ignore") for name in dir_path.split("/")]):
            continue

        for file_name in dir_files:
            if file_name == _ctx.FOLDER_META_FILENAME:
                has_meta = True
            elif file_name == _ctx.REGISTER_PARENT_FILENAME:
                registered_id = _ctx.read_file(f"{dir_path}/{file_name}")
                if registered_id in parent_folders:
                    raise LoadError(
                        f"Parent ID '{registered_id}' was already registered by folder '{parent_folders[registered_id].folder_path}'"
                    )
                _ctx.validate_parent_id(registered_id)
            elif file_name == _ctx.FOLDER_PARENT_FILENAME:
                parent_id = _ctx.read_file(f"{dir_path}/{file_name}")
                if parent_id not in parent_folders:
                    raise LoadError(
                        f"Folder '{dir_path}' can't have parent with ID '{parent_id}' as it does not exist. Did you register the ID in a subfolder of this one?"
                    )
                _ctx.validate_parent_id(parent_id)
            else:
                name, ext = file_name.split(".")
                ext = ext.lower()
                if name.endswith("_ignore"):
                    continue
                if ext == "py" and name.endswith("_meta"):
                    continue
                if ext in _ctx.SUPPORTED_FORMATS:
                    asset_meta = False
                    if os.path.exists(f"{dir_path}/{name}_meta.py"):
                        asset_meta = True
                    asset_pairs.append(
                        _ctx.AssetMetaPair(
                            f"{dir_path}/{file_name}", name, folder_name, asset_meta
                        )
                    )

        if has_meta and parent_id is not None:
            raise LoadError(
                f"Folder '{dir_path}' which declares a parent ID can't have a folder meta as it's handled by the parent folder"
            )
        if parent_id is not None:
            parent_dir = parent_folders[parent_id]
            for ap in asset_pairs:
                ap.folder_name = parent_dir.folder_name
            parent_dir.add_pairs(asset_pairs)
        else:
            asset_folder = _ctx.FolderMeta(dir_path, has_meta, asset_pairs)
            if registered_id:
                parent_folders[registered_id] = asset_folder
            pending_folders.append(asset_folder)

    _ctx.folders = []
    for folder in pending_folders:
        if len(folder.asset_pairs) > 0:
            _ctx.folders.append(folder)

    for folder in _ctx.folders:
        folder.load()


def reload(unit: float = None):
    if unit is not None:
        set_unit(unit)
    if _ctx.load_folder is None:
        raise LoadError("Cannot reload without loading once")

    load(_ctx.load_folder)
    for func in _ctx.refresh_callbacks:
        func()


def refresh(unit: float = None):
    if unit is not None:
        set_unit(unit)
    pgloadermeta.__META_STORAGE__.reset()
    for folder in _ctx.folders:
        folder.load()
    for func in _ctx.refresh_callbacks:
        func()
