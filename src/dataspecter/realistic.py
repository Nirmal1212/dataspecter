"""Generators for the built-in realistic types: names, email addresses and postal addresses.

Phone numbers are generated as patterns and need nothing here.
"""

from __future__ import annotations

import random
from typing import Any

from dataspecter.data import LOCALES, RESERVED_DOMAINS
from dataspecter.generators import Generator, slug
from dataspecter.spec import AddressField, EmailField, NameField

_DIGITS = "0123456789"


def _full_name(field: NameField, given: str, family: str) -> str:
    return f"{family}, {given}" if field.format == "last_first" else f"{given} {family}"


def name_values(field: NameField) -> tuple[int, Any]:
    """Return every value a name field can produce, as a size and an index function."""
    data = LOCALES[field.locale]
    if field.kind == "first_name":
        return len(data.GIVEN_NAMES), data.GIVEN_NAMES.__getitem__
    if field.kind == "last_name":
        return len(data.FAMILY_NAMES), data.FAMILY_NAMES.__getitem__
    families = len(data.FAMILY_NAMES)

    def value_at(index: int) -> str:
        given, family = divmod(index, families)
        return _full_name(field, data.GIVEN_NAMES[given], data.FAMILY_NAMES[family])

    return len(data.GIVEN_NAMES) * families, value_at


def build(field: NameField | EmailField | AddressField, rng: random.Random) -> Generator:
    data = LOCALES[field.locale]
    given, family = data.GIVEN_NAMES, data.FAMILY_NAMES
    match field:
        case NameField(kind="first_name"):
            return lambda: rng.choice(given)
        case NameField(kind="last_name"):
            return lambda: rng.choice(family)
        case NameField():
            return lambda: _full_name(field, rng.choice(given), rng.choice(family))
        case EmailField():
            # Slugged so that a name such as O'Brien still gives a valid address.
            first, last = [slug(name) for name in given], [slug(name) for name in family]
            domains = (field.domain,) if field.domain else RESERVED_DOMAINS
            return lambda: (
                f"{rng.choice(first)}.{rng.choice(last)}{rng.randint(1, 9999)}"
                f"@{rng.choice(domains)}"
            )
        case AddressField():
            return _address(field, rng)
    raise TypeError(f"unsupported field: {field!r}")


def _address(field: AddressField, rng: random.Random) -> Generator:
    data = LOCALES[field.locale]
    wanted = field.fields

    def make() -> dict[str, str]:
        # Everything is drawn whichever fields are wanted, so choosing fewer fields never
        # changes the values of the ones that remain. City, state and postcode prefix come from
        # one record, which is what keeps them consistent with each other.
        city, state, prefixes = rng.choice(data.CITIES)
        prefix = rng.choice(prefixes)
        rest = "".join(rng.choice(_DIGITS) for _ in range(data.POSTCODE_LENGTH - len(prefix)))
        values = {
            "street": f"{rng.randint(1, 999)} {rng.choice(data.STREET_NAMES)}",
            "city": city,
            "state": state,
            "postcode": prefix + rest,
            "country": data.COUNTRY,
        }
        return {name: values[name] for name in wanted}

    return make
