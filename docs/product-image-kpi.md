# Product image operator KPI

kcw-api records who uploaded, replaced, or deleted product pictures from the LINE chatbot. kcw-v2 reads these rows from Supabase for dashboards.

## Source of truth

Table: `ops.product_image_event` (migration `20260813030000_product_image_event.sql`)

| Column | Notes |
|--------|--------|
| `line_user_id` | Operator LINE id from `ops.line_access` |
| `display_name` | Snapshot from access roster at event time |
| `event_type` | `image_upload` · `image_replace` · `image_delete` |
| `bcode` | Product code |
| `storage_path` | Path under bucket (e.g. `product/22010585/22010585.jpg`) |
| `bucket` | Default `pictures` |
| `source` | Default `line_bot` |
| `created_at` | Event time (timestamptz) |

Events are written **only after** Supabase Storage succeeds. Insert failures are logged and do not change the LINE reply.

## Daily rollup (kcw-v2)

View: `ops.product_image_kpi_daily`

One row per operator per Bangkok calendar day:

- `work_date`, `line_user_id`, `display_name`
- `uploads`, `replaces`, `deletes`, `total_actions`, `unique_products`

### Example: today’s leaderboard

```sql
select *
from ops.product_image_kpi_daily
where work_date = (now() at time zone 'Asia/Bangkok')::date
order by total_actions desc, unique_products desc;
```

### Example: date range

```sql
select *
from ops.product_image_kpi_daily
where work_date between :from_date and :to_date
order by work_date desc, total_actions desc;
```

## Activity feed

```sql
select
  created_at,
  display_name,
  line_user_id,
  event_type,
  bcode,
  storage_path
from ops.product_image_event
order by created_at desc
limit 100;
```

Optional join for access group:

```sql
select
  e.*,
  a.access_group
from ops.product_image_event e
left join ops.line_access a on a.line_user_id = e.line_user_id
order by e.created_at desc
limit 100;
```

## Event semantics

| Action | `event_type` |
|--------|----------------|
| New image slot filled | `image_upload` |
| Existing slot overwritten (max 5 reached) | `image_replace` |
| Operator deleted a slot | `image_delete` |

## Notes

- Historical Storage uploads before this migration have no actor and are not backfilled.
- kcw-api does not expose a picture-KPI HTTP endpoint; kcw-v2 queries Supabase directly.
