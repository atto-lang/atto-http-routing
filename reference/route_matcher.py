"""Strict route-pattern reference; excludes HTTP parsing and percent decoding."""
import re

_NAME = re.compile("[a-z][a-z0-9_]{0,63}", re.ASCII)
_LITERAL = re.compile("[A-Za-z0-9_-]{1,128}", re.ASCII)


class RouteError(ValueError):
    pass


def _segments(route, *, pattern):
    if type(route) is not str or not route.startswith("/") or len(route) > 4096:
        raise RouteError("route must be a bounded absolute path")
    if route == "/":
        return ()
    items = route[1:].split("/")
    if len(items) > 64:
        raise RouteError("too many path segments")
    for item in items:
        if not item or item in (".", "..") or "%" in item or "?" in item or "#" in item:
            raise RouteError("invalid or ambiguous route segment")
        if pattern and item.startswith(":"):
            if not _NAME.fullmatch(item[1:]):
                raise RouteError("invalid parameter name")
        elif pattern and not _LITERAL.fullmatch(item):
            raise RouteError("invalid literal segment")
        elif not pattern and (any(ord(c) < 32 or ord(c) == 127 for c in item)
                              or len(item) > 128):
            raise RouteError("invalid path segment")
    return tuple(items)


def compile_route(pattern):
    """Return immutable token plan; parameters are named with a colon prefix."""
    parts = _segments(pattern, pattern=True)
    names = [part[1:] for part in parts if part.startswith(":")]
    if len(names) != len(set(names)):
        raise RouteError("duplicate path parameter")
    return parts


def match_route(pattern, path):
    """Return parameter map for a valid literal path, or None on a nonmatch."""
    parts = compile_route(pattern)
    actual = _segments(path, pattern=False)
    if len(parts) != len(actual):
        return None
    params = {}
    for template, value in zip(parts, actual):
        if template.startswith(":"):
            params[template[1:]] = value
        elif template != value:
            return None
    return params
