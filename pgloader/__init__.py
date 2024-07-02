from . import image, meta

import pygame

assert hasattr(pygame, "IS_CE"), "pygame-ce is required for pgloader, pygame detected"

__all__ = ("image", "meta")
