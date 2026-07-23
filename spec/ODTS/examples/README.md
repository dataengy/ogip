# ODTS 0.1 conformance examples

The six live `spec/sql` models re-authored with `@odts 0.1` headers — the same layout
(`<layer>/<name>.sql`), the same SQL bodies **byte for byte**, only the header differs.
`just standards-validate` asserts all of that: closed directive vocabulary, model-name/path
agreement, and body identity with the corresponding `spec/sql` file, so these fixtures cannot
silently drift from the SSoT they describe.

They are examples of the standard, not the SSoT: the live `spec/sql` files keep their legacy
`@bruin` headers until the `@odts` frontend lands
([#35](https://github.com/dataengy/ogip/issues/35)); both markers are valid during migration.

What the conversion shows, per the profile's inference rule (SPEC.md §4):

- `type: duckdb.sql` is gone — derived from the authoring dialect and file extension;
- `depends:` is gone — derived from the SQL AST (`raw.rawg__games` → `staging.stg_games` →
  `core.game` → `fs.market_features`, and `raw.metacritic__game` →
  `staging.stg_metacritic_games`); it may be authored only as a checked assertion;
- `@bruin` column `checks:` lists collapse into inline attributes (`!null`, `unique`,
  `non_negative`);
- the `raw` model's free-text `description:` has no 0.1 directive — a `doc` directive is
  deferred (SPEC.md §10);
- macro calls (`@keys.hash(game_id)` for `core.game`'s surrogate key) become canonical only
  when the macro registry lands ([#36](https://github.com/dataengy/ogip/issues/36)); until
  then bodies stay identical to the live SQL.
