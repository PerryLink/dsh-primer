# Migration: dsh-primer

This project was previously published as `dsh-plugin-guide`.

- New package: `dsh-primer`
- New repository: https://github.com/PerryLink/dsh-primer
- Old repository: https://github.com/PerryLink/dsh-plugin-guide
- Old npm package: `dsh-plugin-guide@0.3.x`, deprecated, points here
- Legacy record: `LEGACY-0.3.42.md`

Both CLI names work:

```sh
dsh-primer
dsh-plugin-dev   # legacy alias
```

## The old name was reused

`dsh-plugin-guide` 0.4.0 is **not** a compatible update of the old agent skill.
It is a different product: the prose guide and guide skill. The old code stays
in this repository's history, and the old npm versions remain available for
existing installs.

The new guide is at:

- Repository: https://github.com/PerryLink/dsh-plugin-guide
- Package: `dsh-plugin-guide@0.4.0`

New work on the old skill/CLI happens in `dsh-primer`.
