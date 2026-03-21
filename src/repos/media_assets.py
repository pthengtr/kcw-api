from sqlalchemy import text


def search_measurement_guides(
    engine,
    search_terms: list[str],
    object_name: str = "unknown",
    guide_intent: str = "none",
    limit: int = 3,
) -> list[dict]:
    terms = [t.strip() for t in (search_terms or []) if t and t.strip()]

    sql = text("""
        select
            public_url,
            category_key,
            title_th,
            title_en,
            description,
            priority,
            usage_hint,
            tags,
            keywords
        from public.media_assets
        where is_active = true
          and asset_type = 'measurement_guide'
          and (
                (:object_name <> 'unknown' and category_key = :object_name)
             or (:guide_intent <> 'none' and usage_hint = :guide_intent)
             or (coalesce(tags, '{}') && :terms)
             or (coalesce(keywords, '{}') && :terms)
          )
        order by
            case when (:object_name <> 'unknown' and category_key = :object_name) then 0 else 1 end,
            case when (:guide_intent <> 'none' and usage_hint = :guide_intent) then 0 else 1 end,
            priority asc,
            created_at desc
        limit :limit
    """)

    with engine.connect() as conn:
        rows = conn.execute(
            sql,
            {
                "object_name": object_name or "unknown",
                "guide_intent": guide_intent or "none",
                "terms": terms,
                "limit": limit,
            },
        ).mappings().all()

    return [dict(r) for r in rows]