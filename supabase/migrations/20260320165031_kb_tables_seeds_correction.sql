begin;

-- =====================================================
-- kb_sources_seed
-- target columns:
-- source_code, source_name, source_type, source_ref,
-- language, brand, model, is_active
-- =====================================================

alter table if exists curated_kcw.kb_sources_seed
  add column if not exists source_code text,
  add column if not exists source_name text,
  add column if not exists source_type text,
  add column if not exists source_ref text,
  add column if not exists language text,
  add column if not exists brand text,
  add column if not exists model text,
  add column if not exists is_active boolean;

-- =====================================================
-- kb_topics_seed
-- target columns:
-- source_code, topic_code, topic_name, topic_summary,
-- keywords, topic_order, page_from, page_to, parent_topic_name
-- =====================================================

alter table if exists curated_kcw.kb_topics_seed
  add column if not exists source_code text,
  add column if not exists topic_code text,
  add column if not exists topic_name text,
  add column if not exists topic_summary text,
  add column if not exists keywords text,
  add column if not exists topic_order integer,
  add column if not exists page_from integer,
  add column if not exists page_to integer,
  add column if not exists parent_topic_name text;

-- =====================================================
-- kb_chunks_seed
-- target columns:
-- source_code, topic_code, chunk_order, chunk_text,
-- chunk_summary, section_heading, page_from, page_to, token_estimate
-- =====================================================

alter table if exists curated_kcw.kb_chunks_seed
  add column if not exists source_code text,
  add column if not exists topic_code text,
  add column if not exists chunk_order integer,
  add column if not exists chunk_text text,
  add column if not exists chunk_summary text,
  add column if not exists section_heading text,
  add column if not exists page_from integer,
  add column if not exists page_to integer,
  add column if not exists token_estimate integer;

-- kb_sources_seed: drop anything extra
alter table if exists curated_kcw.kb_sources_seed
  drop column if exists created_at,
  drop column if exists updated_at;

-- kb_topics_seed: drop anything extra
alter table if exists curated_kcw.kb_topics_seed
  drop column if exists created_at,
  drop column if exists updated_at;

-- kb_chunks_seed: drop anything extra
alter table if exists curated_kcw.kb_chunks_seed
  drop column if exists created_at,
  drop column if exists updated_at;

commit;