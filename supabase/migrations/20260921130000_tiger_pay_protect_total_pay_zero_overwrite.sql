-- Keep a positive total_pay on success when a later success webhook carries
-- total_pay=0 (e.g. admin confirm on unpaid pendingapproval QR). Status
-- stickiness already exists; this protects v2 qrPromptpayIn money.

create or replace function tiger_pay.ingest_webhook(
    p_event_key text,
    p_body_sha256 text,
    p_transaction jsonb,
    p_payload jsonb
)
returns table(event_id uuid, duplicate boolean, transaction_updated boolean)
language plpgsql
set search_path to 'pg_catalog', 'tiger_pay', 'pg_temp'
as $function$
declare
    v_event_id uuid;
    v_received_at timestamptz := now();

    v_payment_id bigint;
    v_payment_no text;
    v_payment_type text;
    v_payment_status text;

    v_amount numeric(14, 2);
    v_total_pay numeric(14, 2);
    v_change_amount numeric(14, 2);

    v_ref_no_1 text;
    v_ref_no_2 text;
    v_note text;
    v_remark text;

    v_shop_code text;
    v_shop_name text;
    v_branch_name text;

    v_tiger_created_at timestamptz;
    v_tiger_updated_at timestamptz;

    v_transaction_updated boolean := false;
begin
    if p_event_key is null
       or p_event_key !~ '^[0-9a-f]{64}$'
    then
        raise exception using
            errcode = '22023',
            message = 'Invalid Tiger Pay event key';
    end if;

    if p_body_sha256 is null
       or p_body_sha256 !~ '^[0-9a-f]{64}$'
    then
        raise exception using
            errcode = '22023',
            message = 'Invalid Tiger Pay body SHA-256';
    end if;

    if p_transaction is null
       or jsonb_typeof(p_transaction) <> 'object'
    then
        raise exception using
            errcode = '22023',
            message = 'Normalized transaction must be a JSON object';
    end if;

    if p_payload is null
       or jsonb_typeof(p_payload) <> 'object'
    then
        raise exception using
            errcode = '22023',
            message = 'Webhook payload must be a JSON object';
    end if;

    begin
        v_payment_id :=
            nullif(p_transaction ->> 'tiger_payment_id', '')::bigint;

        v_amount :=
            nullif(p_transaction ->> 'amount', '')::numeric(14, 2);

        v_total_pay :=
            nullif(p_transaction ->> 'total_pay', '')::numeric(14, 2);

        v_change_amount :=
            coalesce(
                nullif(
                    p_transaction ->> 'change_amount',
                    ''
                )::numeric(14, 2),
                0
            );

        v_tiger_created_at :=
            nullif(
                p_transaction ->> 'tiger_created_at',
                ''
            )::timestamptz;

        v_tiger_updated_at :=
            nullif(
                p_transaction ->> 'tiger_updated_at',
                ''
            )::timestamptz;

    exception
        when invalid_text_representation
          or numeric_value_out_of_range
          or datetime_field_overflow
        then
            raise exception using
                errcode = '22023',
                message = 'Invalid Tiger Pay number or timestamp';
    end;

    v_payment_no := nullif(p_transaction ->> 'payment_no', '');
    v_payment_type := nullif(lower(p_transaction ->> 'payment_type'), '');
    v_payment_status := nullif(lower(p_transaction ->> 'status'), '');
    v_ref_no_1 := nullif(p_transaction ->> 'ref_no_1', '');
    v_ref_no_2 := nullif(p_transaction ->> 'ref_no_2', '');
    v_note := nullif(p_transaction ->> 'note', '');
    v_remark := nullif(p_transaction ->> 'remark', '');
    v_shop_code := nullif(p_transaction ->> 'shop_code', '');
    v_shop_name := nullif(p_transaction ->> 'shop_name', '');
    v_branch_name := nullif(p_transaction ->> 'branch_name', '');

    if v_payment_id is null or v_payment_id <= 0 then
        raise exception using
            errcode = '22023',
            message = 'Tiger Pay payment ID is required';
    end if;

    if v_payment_no is null then
        raise exception using
            errcode = '22023',
            message = 'Tiger Pay payment number is required';
    end if;

    if v_payment_type is null then
        raise exception using
            errcode = '22023',
            message = 'Tiger Pay payment type is required';
    end if;

    if v_payment_status is null then
        raise exception using
            errcode = '22023',
            message = 'Tiger Pay payment status is required';
    end if;

    insert into tiger_pay.webhook_event (
        event_key,
        body_sha256,
        tiger_payment_id,
        payment_no,
        payment_type,
        payment_status,
        tiger_updated_at,
        received_at,
        payload
    )
    values (
        p_event_key,
        p_body_sha256,
        v_payment_id,
        v_payment_no,
        v_payment_type,
        v_payment_status,
        v_tiger_updated_at,
        v_received_at,
        p_payload
    )
    on conflict (event_key) do nothing
    returning id into v_event_id;

    if v_event_id is null then
        select webhook_event.id
        into v_event_id
        from tiger_pay.webhook_event
        where webhook_event.event_key = p_event_key;

        return query
        select
            v_event_id,
            true,
            false;

        return;
    end if;

    perform pg_advisory_xact_lock(v_payment_id);

    insert into tiger_pay.payment_transaction as current_payment (
        tiger_payment_id,
        payment_no,
        payment_type,
        status,
        amount,
        total_pay,
        change_amount,
        ref_no_1,
        ref_no_2,
        note,
        remark,
        shop_code,
        shop_name,
        branch_name,
        tiger_created_at,
        tiger_updated_at,
        first_received_at,
        last_received_at,
        last_event_id,
        payload
    )
    values (
        v_payment_id,
        v_payment_no,
        v_payment_type,
        v_payment_status,
        v_amount,
        v_total_pay,
        v_change_amount,
        v_ref_no_1,
        v_ref_no_2,
        v_note,
        v_remark,
        v_shop_code,
        v_shop_name,
        v_branch_name,
        v_tiger_created_at,
        v_tiger_updated_at,
        v_received_at,
        v_received_at,
        v_event_id,
        p_payload
    )
    on conflict (tiger_payment_id)
    do update
    set
        payment_no = excluded.payment_no,
        payment_type = excluded.payment_type,
        status = case
            when lower(coalesce(current_payment.status, '')) = 'success'
                 and lower(coalesce(excluded.status, '')) is distinct from 'success'
            then current_payment.status
            else excluded.status
        end,
        amount = excluded.amount,
        total_pay = case
            when lower(coalesce(current_payment.status, '')) = 'success'
                 and coalesce(current_payment.total_pay, 0) > 0
                 and coalesce(excluded.total_pay, 0) = 0
            then current_payment.total_pay
            else excluded.total_pay
        end,
        change_amount = excluded.change_amount,
        ref_no_1 = excluded.ref_no_1,
        ref_no_2 = excluded.ref_no_2,
        note = excluded.note,
        remark = case
            when lower(coalesce(current_payment.status, '')) = 'success'
                 and lower(coalesce(excluded.status, '')) is distinct from 'success'
            then current_payment.remark
            else excluded.remark
        end,
        shop_code = excluded.shop_code,
        shop_name = excluded.shop_name,
        branch_name = excluded.branch_name,
        tiger_created_at = coalesce(
            excluded.tiger_created_at,
            current_payment.tiger_created_at
        ),
        tiger_updated_at = excluded.tiger_updated_at,
        last_received_at = greatest(
            current_payment.last_received_at,
            excluded.last_received_at
        ),
        last_event_id = excluded.last_event_id,
        payload = case
            when lower(coalesce(current_payment.status, '')) = 'success'
                 and lower(coalesce(excluded.status, '')) is distinct from 'success'
            then current_payment.payload
            when lower(coalesce(current_payment.status, '')) = 'success'
                 and coalesce(current_payment.total_pay, 0) > 0
                 and coalesce(excluded.total_pay, 0) = 0
            then jsonb_set(
                coalesce(excluded.payload, '{}'::jsonb),
                '{payment,totalPay}',
                to_jsonb(current_payment.total_pay),
                true
            )
            else excluded.payload
        end
    where
        current_payment.tiger_updated_at is null
        or (
            excluded.tiger_updated_at is not null
            and excluded.tiger_updated_at
                >= current_payment.tiger_updated_at
        )
    returning true into v_transaction_updated;

    v_transaction_updated := coalesce(v_transaction_updated, false);

    if not v_transaction_updated then
        update tiger_pay.payment_transaction
        set last_received_at = greatest(
            last_received_at,
            v_received_at
        )
        where tiger_payment_id = v_payment_id;
    end if;

    return query
    select
        v_event_id,
        false,
        v_transaction_updated;
end;
$function$;
