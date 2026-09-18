# Slug contract

`slugify(title)` accepts a nonempty string. ASCII letters become lowercase,
digits remain, and each maximal run of other characters becomes one hyphen;
leading/trailing hyphens are removed. A value with no resulting alphanumeric
characters, or a non-string input, raises `ValueError`.

The checked-in implementation deliberately lacks part of this behavior. This
trial is test authoring only: production must remain unchanged, and a correct
new test may make the current full suite red.
