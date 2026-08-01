# Contributing

The list rots. Directories die, get bought, drop their dofollow links, or quietly start charging. Corrections are the most valuable thing you can send.

## Fixing an entry

Edit [`data/directories.json`](data/directories.json) and say what you saw:

- **Dead / parked / 404** — remove the entry, note what you got in the PR body.
- **DR moved** — DR comes from Ahrefs and is refreshed weekly; if yours is newer, say where it came from.
- **Link type wrong** — this one matters most. `dofollow: true` means someone checked the rendered `rel` attribute on a live listing. If you have a listing there and the link is `nofollow`, that is a bug in our data — please fix it.
- **Price changed** — `free`, `freemium` or `paid` for the *entry* tier.

`directories.md` is generated from the JSON, so edit the JSON and mention it; the table gets rebuilt.

## Adding a directory

Send it if it clears all four:

1. It is a place you can **submit a product**, not a blog post about directories.
2. It is **alive** — a submission in the last 6 months got approved.
3. It has a **working submission path** that does not require paying to be seen at all.
4. It is not already in the list under another domain.

```json
{
  "name": "Example Directory",
  "domain": "example.com",
  "url": "https://example.com",
  "dr": 42,
  "dofollow": true,
  "pricing": "free",
  "category": "SaaS directory",
  "source": "community"
}
```

Leave `dr` out rather than guessing it. A wrong number is worse than a missing one.

## What gets rejected

- Link farms, PBNs, and "submit to 500 directories" services.
- Directories that are pure paywalls with no free path.
- Your own directory, added in the same PR as three others of yours.
- Bulk PRs adding a dozen unverified entries.

## Data

`data/` is CC BY 4.0 — take it, ship it, build on it. Attribution line: *"Directory data: SaaSCity Launch Kit (CC BY 4.0)"*. Domain Ratings are Ahrefs'.
