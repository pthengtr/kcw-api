begin;

create table if not exists curated_kcw.kb_sources (
  source_id bigserial primary key,
  source_code text not null unique,
  source_name text not null,
  source_type text not null,
  source_ref text null,
  language text null default 'th',
  brand text null,
  model text null,
  is_active boolean not null default true,
  created_at timestamp with time zone not null default now(),
  updated_at timestamp with time zone not null default now()
);

create table if not exists curated_kcw.kb_topics (
  topic_id bigserial primary key,
  source_id bigint not null references curated_kcw.kb_sources(source_id) on delete cascade,
  topic_code text not null,
  topic_name text not null,
  topic_summary text not null,
  keywords text null,
  topic_order integer null,
  page_from integer null,
  page_to integer null,
  is_active boolean not null default true,
  created_at timestamp with time zone not null default now(),
  updated_at timestamp with time zone not null default now(),
  constraint kb_topics_source_topic_code_key unique (source_id, topic_code)
);

create index if not exists idx_kb_topics_source_id
  on curated_kcw.kb_topics(source_id);

create index if not exists idx_kb_topics_topic_name
  on curated_kcw.kb_topics(topic_name);

create table if not exists curated_kcw.kb_chunks (
  chunk_id bigserial primary key,
  topic_id bigint not null references curated_kcw.kb_topics(topic_id) on delete cascade,
  chunk_order integer not null,
  chunk_text text not null,
  chunk_summary text null,
  section_heading text null,
  page_from integer null,
  page_to integer null,
  token_estimate integer null,
  is_active boolean not null default true,
  created_at timestamp with time zone not null default now(),
  updated_at timestamp with time zone not null default now(),
  constraint kb_chunks_topic_order_key unique (topic_id, chunk_order)
);

create index if not exists idx_kb_chunks_topic_id
  on curated_kcw.kb_chunks(topic_id);

commit;