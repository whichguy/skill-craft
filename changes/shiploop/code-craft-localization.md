---
bump: minor
---
Code craft gains rule 7, *Write text that can be translated*: user-facing
messages go through the repository's message catalog when one exists, and
otherwise stay whole sentences with named placeholders so they can be
externalized later. Numbers, dates, currency and plurals use locale-aware
APIs, and logs, error codes and identifiers stay untranslated. The quality
loop reviews for concatenated or catalog-bypassing text, and a new
Localization practice card in the coding decision guide covers catalogs,
plurals, explicit locales, UI expansion and right-to-left layout, and tests.
