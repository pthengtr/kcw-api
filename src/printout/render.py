import html
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from src.printout.schema import BLANK_OUTPUT_COLUMNS, PRINTOUT_COLUMN_LABELS, PRINTOUT_COLUMNS

BANGKOK_TZ = ZoneInfo("Asia/Bangkok")


def _fmt_ts(epoch: float | None) -> str:
    if not epoch:
        return "-"
    try:
        dt = datetime.fromtimestamp(epoch, tz=BANGKOK_TZ)
        be_year = dt.year + 543
        yy = be_year % 100
        return dt.strftime(f"%d/%m/{yy:02d} %H:%M")
    except Exception:
        return "-"


def render_printout_html(printout: dict[str, Any]) -> str:
    extracted = printout.get("extracted") or {}
    title = html.escape(str(extracted.get("title") or "รายการจากตาราง"))
    columns = list(PRINTOUT_COLUMNS)
    rows = extracted.get("rows") or []
    warnings = extracted.get("warnings") or []
    error = extracted.get("error")
    created_at = _fmt_ts(printout.get("created_at"))
    expires_at = _fmt_ts(printout.get("expires_at"))

    def _col_label(col: str) -> str:
        return PRINTOUT_COLUMN_LABELS.get(col, col)

    header_cells = "".join(
        f"<th>{html.escape(_col_label(col))}</th>" for col in columns
    )

    body_rows = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        cells = []
        for col in columns:
            if col in BLANK_OUTPUT_COLUMNS:
                cells.append('<td class="blank-cell">&nbsp;</td>')
            else:
                cells.append(
                    f"<td>{html.escape(str(row.get(col, '') or ''))}</td>"
                )
        cells = "".join(cells)
        body_rows.append(f"<tr>{cells}</tr>")

    warnings_html = ""
    if warnings:
        warning_items = "".join(f"<li>{html.escape(str(w))}</li>" for w in warnings)
        warnings_html = f"""
        <section class="warnings">
          <h2>หมายเหตุจากการสแกน</h2>
          <ul>{warning_items}</ul>
        </section>
        """

    error_html = ""
    if error:
        error_html = f"""
        <section class="error">
          <strong>ไม่สามารถสแกนตารางได้:</strong> {html.escape(str(error))}
        </section>
        """

    table_html = ""
    if columns and body_rows:
        table_html = f"""
        <table>
          <thead><tr>{header_cells}</tr></thead>
          <tbody>{''.join(body_rows)}</tbody>
        </table>
        """
    else:
        table_html = '<p class="empty">ไม่พบข้อมูลตารางจากรูปนี้</p>'

    signature_html = """
    <section class="signature">
      <div class="signature-box">
        <div class="signature-title">ตรวจสอบสินค้าแล้ว</div>
        <div class="signature-space"></div>
        <div class="signature-meta">
          <span>ลายเซ็น</span>
          <span>วันที่</span>
        </div>
      </div>
    </section>
    """

    return f"""<!DOCTYPE html>
<html lang="th">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <style>
    :root {{
      color-scheme: light;
      font-family: "Sarabun", "Noto Sans Thai", sans-serif;
    }}
    body {{
      margin: 0;
      padding: 24px;
      color: #111;
      background: #f7f7f7;
    }}
    .sheet {{
      max-width: 1100px;
      margin: 0 auto;
      background: #fff;
      padding: 24px;
      border: 1px solid #ddd;
      border-radius: 8px;
    }}
    h1 {{
      margin: 0 0 8px;
      font-size: 24px;
    }}
    .meta {{
      color: #555;
      font-size: 14px;
      margin-bottom: 20px;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 14px;
    }}
    th, td {{
      border: 1px solid #333;
      padding: 8px 10px;
      text-align: left;
      vertical-align: top;
    }}
    th {{
      background: #efefef;
    }}
    .blank-cell {{
      min-width: 72px;
      height: 28px;
      background: #fff;
    }}
    .signature {{
      margin-top: 32px;
    }}
    .signature-box {{
      max-width: 360px;
      margin-left: auto;
      border: 1px solid #333;
      padding: 16px;
    }}
    .signature-title {{
      font-size: 16px;
      font-weight: 600;
      margin-bottom: 12px;
      text-align: center;
    }}
    .signature-space {{
      height: 72px;
      border-bottom: 1px solid #333;
      margin-bottom: 10px;
    }}
    .signature-meta {{
      display: flex;
      justify-content: space-between;
      font-size: 13px;
      color: #555;
    }}
    .warnings {{
      margin-top: 20px;
      padding: 12px 16px;
      background: #fff8e1;
      border: 1px solid #f0c36d;
      border-radius: 6px;
    }}
    .error {{
      margin-bottom: 16px;
      padding: 12px 16px;
      background: #ffebee;
      border: 1px solid #ef9a9a;
      border-radius: 6px;
    }}
    .empty {{
      color: #666;
    }}
    .actions {{
      margin-top: 20px;
    }}
    button {{
      font-size: 16px;
      padding: 10px 16px;
      cursor: pointer;
    }}
    @media print {{
      body {{
        background: #fff;
        padding: 0;
      }}
      .sheet {{
        border: none;
        border-radius: 0;
        padding: 0;
      }}
      .actions {{
        display: none;
      }}
    }}
  </style>
</head>
<body>
  <div class="sheet">
    <h1>{title}</h1>
    <div class="meta">สร้างเมื่อ {created_at} | หมดอายุ {expires_at}</div>
    {error_html}
    {table_html}
    {warnings_html}
    {signature_html}
    <div class="actions">
      <button type="button" onclick="window.print()">พิมพ์</button>
    </div>
  </div>
</body>
</html>"""
