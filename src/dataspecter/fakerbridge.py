"""The bridge to the optional Faker library. This is the only module that imports it.

A spec is data, and the `faker` field type is the one place where a spec names something to
call. The boundary is kept narrow: only methods that Faker's providers define can be called,
only plain values can be passed, and only single values are accepted back.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import date
from decimal import Decimal
from functools import lru_cache
from typing import Any

from dataspecter.errors import GenerationError

NOT_INSTALLED = (
    "the 'faker' type needs the Faker library, which is not installed; "
    "install it with: pip install faker"
)


def _faker_class() -> Any:
    try:
        from faker import Faker
    except ImportError:
        return None
    return Faker


@lru_cache(maxsize=32)
def _probe_instance(locale: str) -> Any:
    return _make(locale)


def _make(locale: str) -> Any:
    try:
        return _faker_class()(locale)
    except AttributeError:
        raise ValueError(f"Faker does not support the locale {locale!r}") from None


def _method(fake: Any, provider: str) -> Callable[..., Any] | None:
    """Return the provider method of that name, or None if it is not one.

    Names starting with an underscore, and methods of the Faker object itself such as
    `seed_instance`, are not provider methods and are refused.
    """
    if provider.startswith("_"):
        return None
    if any(callable(getattr(source, provider, None)) for source in fake.get_providers()):
        return getattr(fake, provider)
    return None


def _convert(value: Any) -> tuple[bool, Any]:
    """Return whether a provider's result is a single supported value, and that value."""
    if isinstance(value, Decimal):
        return True, float(value)
    if isinstance(value, str | bool | int | float | date):  # date covers datetime
        return True, value
    return False, value


def check(provider: str, locale: str, args: Mapping[str, Any]) -> str | None:
    """Try the provider once. Return what is wrong, or None if the field can be used."""
    if _faker_class() is None:
        return NOT_INSTALLED
    try:
        fake = _probe_instance(locale)
    except ValueError as error:
        return str(error)
    method = _method(fake, provider)
    if method is None:
        if hasattr(fake, provider) or provider.startswith("_"):
            return f"{provider!r} is not a Faker provider"
        return f"Faker has no provider named {provider!r} for the locale {locale!r}"
    try:
        result = method(**args)
    except Exception as error:  # whatever the provider raises is a problem with the field
        return f"Faker provider {provider!r} could not be called: {error}"
    supported, _ = _convert(result)
    if not supported:
        kind = type(result).__name__
        return (
            f"Faker provider {provider!r} does not return a single value (it returned a "
            f"{kind}); only text, numbers, booleans, dates and date-times are supported"
        )
    return None


def generator(field: Any, seed: int, label: str) -> Callable[[], Any]:
    """Return a function producing the field's next value from its own seeded Faker."""
    fake = _make(field.locale)
    fake.seed_instance(seed)
    method = _method(fake, field.provider)
    args = dict(field.args)

    def generate() -> Any:
        supported, value = _convert(method(**args))
        if not supported:
            # One trial call at validation does not prove a provider always returns one kind.
            raise GenerationError(
                f"{label}: Faker provider {field.provider!r} returned a "
                f"{type(value).__name__}, which is not a single supported value"
            )
        return value

    return generate
