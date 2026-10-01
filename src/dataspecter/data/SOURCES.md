# Sources of the bundled data

Every list in this package is recorded here with where it came from, under what terms it is redistributed, and whether it has been checked against an authoritative source.

| List | Locales | Source | Licence | Checked against an authority |
|---|---|---|---|---|
| Given names | `en_IN`, `en_US` | Written by hand for this project: common names from general knowledge. Not copied from any dataset. | Project licence. Individual names are not subject to copyright. | Not applicable |
| Family names | `en_IN`, `en_US` | Written by hand, as above. | Project licence. | Not applicable |
| Street names | `en_IN`, `en_US` | Written by hand: common street names, not tied to any city. | Project licence. | Not applicable |
| Cities and their states | `en_IN`, `en_US` | Written by hand from general knowledge. | Project licence. Facts about places are not subject to copyright. | **No. Needs review.** |
| Postcode prefixes per city | `en_IN` (PIN), `en_US` (ZIP) | Written by hand from general knowledge of each city's main postcode range. | Project licence. | **No. Needs review.** |
| Phone formats | `en_IN`, `en_US` | The public national numbering formats. The `en_US` range 555-0100 to 555-0199 is the one reserved for fictional use. | Not applicable | Format only |
| Reserved email domains | all | RFC 2606 (`example.com`, `example.org`, `example.net`). | Not applicable | Yes |

## What "needs review" means

The city-to-state and city-to-postcode-prefix rows were written from memory and have **not** been compared with the India Post PIN code directory or the United States Postal Service ZIP code data. They are believed correct for the main postcode range of each city, but a wrong prefix would produce addresses that look consistent and are not.

Before a release, someone should check each row of `CITIES` in `en_in.py` and `en_us.py` against the postal authority's published data and tick it off in the pull request. The automated tests check structure only: sizes, duplicates, that every state is in the locale's `STATES` list, and that every prefix has three digits.

## Limits of the data

- Names are chosen uniformly. They do not follow the frequencies of a real population.
- One prefix is recorded per city, so generated postcodes cover only part of a large city's real range, and the digits after the prefix are random: a full postcode may not be one in use.
- Streets are a house number and a common street name. They are not real addresses.
