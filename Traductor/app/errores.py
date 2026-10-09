# -*- coding: utf-8 -*-
"""Errores compartidos entre los módulos."""


class ErrorTraduccion(Exception):
    """Falla al traducir, con un mensaje pensado para mostrarse al usuario.
    Cualquier motor de traducción debe lanzar este error."""
