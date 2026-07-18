"""SQL dialect layer (SQLGlot) — the engine-agnostic half of the compiler (ADR-0005/0016).

`spec/sql` is authored portable (DuckDB/Postgres-first). Everything that has to *understand*
that SQL — rewriting refs, deriving lineage, retargeting a dialect — parses it into an AST
here instead of pattern-matching text. The difference is not stylistic: a regex rewrites
`staging.stg_games` inside a string literal or a comment just as happily as in a `FROM`
clause, and silently ships the wrong SQL. The AST only ever touches real table references.

The production path stays DuckDB; `transpile` exists so a spec model can be retargeted
(Postgres landing, ClickHouse, BigQuery) without forking the spec — the portable-SQL policy
made executable rather than merely documented.
"""

from __future__ import annotations

import sqlglot
import sqlglot.expressions as exp  # module: value access (exp.Table, exp.alias_) needs no re-export
from sqlglot.errors import ParseError
from sqlglot.expressions.core import Expr  # the base node type, from its defining module

SPEC_DIALECT = "duckdb"  # the dialect spec/sql is authored in


class SqlSpecError(ValueError):
    """`spec/sql` contains SQL that will not parse — a compile-time failure, not a runtime one."""


def parse(sql: str, *, read: str = SPEC_DIALECT) -> Expr:
    """Parse one spec statement; raise :class:`SqlSpecError` with context on failure."""
    if not sql.strip():  # parse_one returns None here — guard up front so the type stays Expr
        raise SqlSpecError("empty SQL statement")
    try:
        return sqlglot.parse_one(sql, read=read)
    except ParseError as err:
        raise SqlSpecError(f"unparseable {read} SQL: {err}") from err


def table_refs(sql: str, *, read: str = SPEC_DIALECT) -> list[str]:
    """Every table this SQL reads, as `schema.table` (CTE names excluded — they are local).

    This is lineage derived from the SQL itself, so it can be checked against the `depends`
    a spec author wrote by hand; the two disagreeing means one of them is wrong.
    """
    tree = parse(sql, read=read)
    ctes = {cte.alias_or_name for cte in tree.find_all(exp.CTE)}
    refs: list[str] = []
    for table in tree.find_all(exp.Table):
        if table.name in ctes and not table.db:
            continue
        name = f"{table.db}.{table.name}" if table.db else table.name
        if name not in refs:
            refs.append(name)
    return refs


def rewrite_refs(
    sql: str, mapping: dict[str, str], *, read: str = SPEC_DIALECT, pretty: bool = True
) -> str:
    """Replace `schema.table` references per ``mapping`` — AST-scoped, never inside literals.

    Values are emitted verbatim (they are engine templates such as ``{{ ref('stg_games') }}``,
    not SQL), so the result is a rendered template rather than a re-parseable statement.
    """
    tree = parse(sql, read=read)

    def _replace(node: Expr) -> Expr:
        if isinstance(node, exp.Table) and node.db:
            target = mapping.get(f"{node.db}.{node.name}")
            if target is not None:
                # `alias_` keeps `from staging.stg_games s` working after the swap.
                replacement = exp.to_identifier(target, quoted=False)
                return exp.alias_(replacement, node.alias) if node.alias else replacement
        return node

    # pretty: the generated projects are read by humans during engine comparisons.
    return tree.transform(_replace).sql(dialect=read, pretty=pretty)


def transpile(sql: str, *, write: str, read: str = SPEC_DIALECT) -> str:
    """Retarget one spec statement to another engine's dialect (portable-SQL policy)."""
    try:
        rendered = sqlglot.transpile(sql, read=read, write=write)
    except ParseError as err:
        raise SqlSpecError(f"cannot transpile {read} -> {write}: {err}") from err
    if not rendered:
        raise SqlSpecError("empty SQL statement")
    return rendered[0]
