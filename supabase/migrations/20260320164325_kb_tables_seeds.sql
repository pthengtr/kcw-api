create table curated_kcw.kb_sources_seed (
  source_code text,
  source_name text,
  source_type text,
  source_ref text,
  language text,
  brand text,
  model text
);

create table curated_kcw.kb_topics_seed (
  source_code text,
  topic_code text,
  topic_name text,
  parent_topic_name text,
  topic_order int,
  page_from int,
  page_to int
);

create table curated_kcw.kb_chunks_seed (
  source_code text,
  topic_code text,
  chunk_order int,
  chunk_text text,
  section_heading text,
  page_from int,
  page_to int
);