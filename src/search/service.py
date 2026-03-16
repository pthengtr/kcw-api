import pandas as pd

from .config import (
    CODE_FIELDS,
    TEXT_FIELDS,
    CODE_WEIGHTS,
    TEXT_WEIGHTS,
    TOKEN_TEXT_WEIGHTS,
    TOKEN_CODE_WEIGHTS,
)
from .models import SearchQuery


def empty_search_result_df() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "BCODE", "XCODE", "MCODE", "PCODE", "ACODE",
            "DESCR", "MODEL", "BRAND", "PRICE1",
            "matched_column", "match_type", "matched_terms", "score",
        ]
    )


def base_select_sql() -> str:
    return """
        trim("BCODE") as "BCODE",
        trim("XCODE") as "XCODE",
        trim("MCODE") as "MCODE",
        trim("PCODE") as "PCODE",
        trim("ACODE") as "ACODE",
        trim("DESCR") as "DESCR",
        trim("MODEL") as "MODEL",
        trim("BRAND") as "BRAND",
        "PRICE1"
    """


def make_or_equals(fields: list[str], param_name: str) -> str:
    return " or ".join([f'trim("{field}") = %({param_name})s' for field in fields])


def make_or_ilike(fields: list[str], param_name: str) -> str:
    return " or ".join([f'trim("{field}") ilike %({param_name})s' for field in fields])


def make_case_match_column(
    fields: list[str],
    match_rules: list[tuple[str, str]],
    default: str | None = None,
) -> str:
    lines = ["case"]
    for op, param_name in match_rules:
        for field in fields:
            lines.append(f'    when trim("{field}") {op} %({param_name})s then \'{field}\'')
    if default is not None:
        lines.append(f"    else '{default}'")
    lines.append("end")
    return "\n".join(lines)


def make_case_weight_sum(weight_map: dict[str, int], op: str, param_name: str) -> str:
    parts = []
    for field, weight in weight_map.items():
        parts.append(f'case when trim("{field}") {op} %({param_name})s then {weight} else 0 end')
    return " + ".join(parts) if parts else "0"


def make_three_level_score_sql(
    weights: dict[str, dict[str, int]],
    exact_param: str,
    prefix_param: str,
    partial_param: str,
) -> str:
    parts = [
        make_case_weight_sum(weights.get("exact", {}), "ilike", exact_param),
        make_case_weight_sum(weights.get("prefix", {}), "ilike", prefix_param),
        make_case_weight_sum(weights.get("partial", {}), "ilike", partial_param),
    ]
    return " + ".join([f"({p})" for p in parts if p])


def make_code_exact_score_sql() -> str:
    parts = []
    for field, weight in CODE_WEIGHTS["exact"].items():
        parts.append(f'case when trim("{field}") = %(q)s then {weight} else 0 end')
    return " + ".join(parts)


def make_code_partial_score_sql() -> str:
    prefix_sql = make_case_weight_sum(CODE_WEIGHTS["prefix"], "ilike", "q_prefix")
    partial_sql = make_case_weight_sum(CODE_WEIGHTS["partial"], "ilike", "q_like")
    return f"({prefix_sql}) + ({partial_sql})"


def make_phrase_text_score_sql() -> str:
    exact_sql = make_case_weight_sum(TEXT_WEIGHTS["exact"], "ilike", "q_exact")
    prefix_sql = make_case_weight_sum(TEXT_WEIGHTS["prefix"], "ilike", "q_prefix")
    partial_sql = make_case_weight_sum(TEXT_WEIGHTS["partial"], "ilike", "q_like")
    return f"({exact_sql}) + ({prefix_sql}) + ({partial_sql})"


def build_token_sql_parts(sq: SearchQuery) -> tuple[str, str, str]:
    token_where_parts = []
    token_score_parts = []
    token_match_count_parts = []

    searchable_fields = CODE_FIELDS + TEXT_FIELDS

    for i, _term in enumerate(sq.terms):
        like_key = f"term_like_{i}"
        prefix_key = f"term_prefix_{i}"
        exact_key = f"term_exact_{i}"

        token_where_parts.append(
            "(" + " or ".join(
                [f'trim("{field}") ilike %({like_key})s' for field in searchable_fields]
            ) + ")"
        )

        token_code_score = make_three_level_score_sql(
            TOKEN_CODE_WEIGHTS,
            exact_param=exact_key,
            prefix_param=prefix_key,
            partial_param=like_key,
        )

        token_text_score = make_three_level_score_sql(
            TOKEN_TEXT_WEIGHTS,
            exact_param=exact_key,
            prefix_param=prefix_key,
            partial_param=like_key,
        )

        token_score_parts.append(f"(({token_code_score}) + ({token_text_score}))")

        token_match_count_parts.append(
            "case when "
            + " or ".join([f'trim("{field}") ilike %({like_key})s' for field in searchable_fields])
            + " then 1 else 0 end"
        )

    token_where_sql = " or ".join(token_where_parts) if token_where_parts else "false"
    token_score_sql = " + ".join([f"({x})" for x in token_score_parts]) if token_score_parts else "0"
    token_match_count_sql = " + ".join([f"({x})" for x in token_match_count_parts]) if token_match_count_parts else "0"

    return token_where_sql, token_score_sql, token_match_count_sql


def build_exact_code_block(sq: SearchQuery) -> str:
    match_column_sql = make_case_match_column(CODE_FIELDS, match_rules=[("=", "q")])
    where_sql = make_or_equals(CODE_FIELDS, "q")
    score_sql = make_code_exact_score_sql()

    return f"""
        select
            {base_select_sql()},
            {match_column_sql} as matched_column,
            'exact_code' as match_type,
            {max(sq.term_count, 1)} as matched_terms,
            ({score_sql}) as score
        from raw_kcw.raw_hq_icmas_products
        where {where_sql}
    """


def build_partial_code_block() -> str:
    match_column_sql = make_case_match_column(CODE_FIELDS, match_rules=[("ilike", "q_like")])
    where_sql = make_or_ilike(CODE_FIELDS, "q_like")
    score_sql = make_code_partial_score_sql()

    return f"""
        select
            {base_select_sql()},
            {match_column_sql} as matched_column,
            'partial_code' as match_type,
            1 as matched_terms,
            ({score_sql}) as score
        from raw_kcw.raw_hq_icmas_products
        where {where_sql}
    """


def build_phrase_text_block() -> str:
    match_column_sql = make_case_match_column(
        TEXT_FIELDS,
        match_rules=[
            ("ilike", "q_exact"),
            ("ilike", "q_prefix"),
            ("ilike", "q_like"),
        ],
    )
    where_sql = make_or_ilike(TEXT_FIELDS, "q_like")
    score_sql = make_phrase_text_score_sql()

    return f"""
        select
            {base_select_sql()},
            {match_column_sql} as matched_column,
            'phrase_text' as match_type,
            1 as matched_terms,
            ({score_sql}) as score
        from raw_kcw.raw_hq_icmas_products
        where {where_sql}
    """


def build_token_mixed_block(token_where_sql: str, token_score_sql: str, token_match_count_sql: str) -> str:
    return f"""
        select
            {base_select_sql()},
            'MIXED' as matched_column,
            'token_mixed' as match_type,
            ({token_match_count_sql}) as matched_terms,
            ({token_score_sql}) as score
        from raw_kcw.raw_hq_icmas_products
        where {token_where_sql}
    """


def query_product_search_v3(engine, search_query: SearchQuery) -> pd.DataFrame:
    if search_query.is_empty:
        return empty_search_result_df()

    params = search_query.to_sql_params()
    token_where_sql, token_score_sql, token_match_count_sql = build_token_sql_parts(search_query)

    candidate_blocks = [
        build_exact_code_block(search_query),
        build_partial_code_block(),
        build_phrase_text_block(),
        build_token_mixed_block(
            token_where_sql=token_where_sql,
            token_score_sql=token_score_sql,
            token_match_count_sql=token_match_count_sql,
        ),
    ]

    candidates_sql = "\nunion all\n".join(candidate_blocks)

    sql = f"""
    with candidates as (
        {candidates_sql}
    ),
    ranked as (
        select *,
               row_number() over (
                   partition by "BCODE"
                   order by matched_terms desc, score desc, match_type
               ) as rn
        from candidates
    )
    select
        "BCODE",
        "XCODE",
        "MCODE",
        "PCODE",
        "ACODE",
        "DESCR",
        "MODEL",
        "BRAND",
        "PRICE1",
        matched_column,
        match_type,
        matched_terms,
        score
    from ranked
    where rn = 1
    order by matched_terms desc, score desc, "BCODE"
    limit %(limit)s
    """

    return pd.read_sql(sql, engine, params=params)


def search_products(engine, raw_query: str, limit: int = 20) -> pd.DataFrame:
    sq = SearchQuery(raw=raw_query, limit=limit)
    return query_product_search_v3(engine, sq)

def get_product_detail_by_bcode(engine, bcode: str) -> pd.DataFrame:
    sql = """
    select
        trim("BCODE") as "BCODE",
        trim("XCODE") as "XCODE",
        trim("MCODE") as "MCODE",
        trim("PCODE") as "PCODE",
        trim("ACODE") as "ACODE",
        trim("DESCR") as "DESCR",
        trim("MODEL") as "MODEL",
        trim("BRAND") as "BRAND",
        "PRICE1"
    from raw_kcw.raw_hq_icmas_products
    where trim("BCODE") = %(bcode)s
    limit 1
    """
    return pd.read_sql(sql, engine, params={"bcode": bcode.strip()})