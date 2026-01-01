# -*- coding: utf-8 -*-

"""
API v1 - SoulVerse

Ce module contient toutes les routes de l'API version 1.
"""

# Export des routers pour faciliter les imports
from . import user, verses, scheduler, prayers

__all__ = ["user", "verses", "scheduler", "prayers"]
