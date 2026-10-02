"""Bundled data for the built-in realistic types, one module per locale."""

from dataspecter.data import en_in, en_us

DEFAULT_LOCALE = "en_US"
LOCALES = {"en_US": en_us, "en_IN": en_in}

# Reserved for documentation by RFC 2606, so an address at one of them cannot reach a mailbox.
RESERVED_DOMAINS = ("example.com", "example.org", "example.net")

ADDRESS_FIELDS = ("street", "city", "state", "postcode", "country")
