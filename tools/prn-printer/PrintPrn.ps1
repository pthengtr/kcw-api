param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string]$Path
)

$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

if (-not (Test-Path -LiteralPath $Path)) {
    [System.Windows.Forms.MessageBox]::Show("File not found:`n$Path", 'Print PRN', 'OK', 'Error') | Out-Null
    exit 1
}

$__prnRoot = if ($env:KCW_PRN_PRINTER_HOME) { $env:KCW_PRN_PRINTER_HOME.TrimEnd('\') } else { Split-Path -Parent $MyInvocation.MyCommand.Path }
$zxingPath = Join-Path $__prnRoot 'lib\zxing.dll'
$zxingPresPath = Join-Path $__prnRoot 'lib\zxing.presentation.dll'
$script:zxingOk = (Test-Path -LiteralPath $zxingPath) -and (Test-Path -LiteralPath $zxingPresPath)
if ($script:zxingOk) {
    Add-Type -Path $zxingPath
    Add-Type -Path $zxingPresPath
}

function Get-LocalPrnVersion {
    $verFile = Join-Path $__prnRoot 'VERSION.json'
    if (-not (Test-Path -LiteralPath $verFile)) { return $null }
    try { return (Get-Content -LiteralPath $verFile -Raw -Encoding UTF8 | ConvertFrom-Json).version } catch { return $null }
}

function Get-UpdateBaseUrl {
    if ($env:KCW_PRN_UPDATE_BASE) { return $env:KCW_PRN_UPDATE_BASE.TrimEnd('/') }
    $f = Join-Path $__prnRoot 'update-base.txt'
    if (Test-Path -LiteralPath $f) {
        $u = (Get-Content -LiteralPath $f -TotalCount 1 -ErrorAction SilentlyContinue)
        if ($u) { return $u.Trim().TrimEnd('/') }
    }
    return $null
}

function Get-RemotePrnVersion([string]$BaseUrl) {
    try {
        $resp = Invoke-WebRequest -Uri "$BaseUrl/tools/prn-printer/version" -UseBasicParsing -TimeoutSec 2
        return ($resp.Content | ConvertFrom-Json).version
    } catch {
        return $null
    }
}

function Compare-PrnVersion([string]$A, [string]$B) {
    # returns 1 if A>B, 0 if equal, -1 if A<B (numeric dotted)
    $pa = @($A -split '\.' | ForEach-Object { if ($_ -match '^\d+$') { [int]$_ } else { 0 } })
    $pb = @($B -split '\.' | ForEach-Object { if ($_ -match '^\d+$') { [int]$_ } else { 0 } })
    $n = [Math]::Max($pa.Count, $pb.Count)
    for ($i = 0; $i -lt $n; $i++) {
        $x = if ($i -lt $pa.Count) { $pa[$i] } else { 0 }
        $y = if ($i -lt $pb.Count) { $pb[$i] } else { 0 }
        if ($x -gt $y) { return 1 }
        if ($x -lt $y) { return -1 }
    }
    return 0
}

$script:localPrnVersion = Get-LocalPrnVersion
$script:updateHint = $null
$updateBase = Get-UpdateBaseUrl
if ($updateBase -and $script:localPrnVersion) {
    $remoteVer = Get-RemotePrnVersion -BaseUrl $updateBase
    if ($remoteVer -and (Compare-PrnVersion $remoteVer $script:localPrnVersion) -gt 0) {
        $script:updateHint = "Update available: v$remoteVer (you have v$($script:localPrnVersion)). Re-run: irm $updateBase/tools/prn-printer/install.ps1 | iex"
    }
}

Add-Type -ReferencedAssemblies @('System.Drawing.dll') -TypeDefinition @"
using System;
using System.IO;
using System.Drawing;
using System.Drawing.Imaging;
using System.Collections.Generic;
using System.Runtime.InteropServices;
using System.Text;
using System.Text.RegularExpressions;

public static class PrnPreview {
    public class BitmapPart {
        public int X;
        public int Y;
        public int WidthBytes;
        public int Height;
        public byte[] Data;
        public int Sets = 1;
        public int Copies = 1;
        public string Barcode = "";
        public int PrintCount { get { return Sets * Copies; } }
    }

    public class PrintJob {
        public int Sets;
        public int Copies;
        public string Raw;
        public int Total { get { return Sets * Copies; } }
    }

    public class ParseResult {
        public double WidthMm;
        public double HeightMm;
        public bool HasSize;
        public bool Bit0Prints;
        public List<BitmapPart> Bitmaps = new List<BitmapPart>();
        public List<PrintJob> PrintJobs = new List<PrintJob>();
        public int TotalLabels {
            get {
                int sum = 0;
                foreach (var j in PrintJobs) sum += j.Total;
                return sum;
            }
        }
    }

    static bool IsCommandStart(byte[] bytes, int k) {
        return k == 0 || bytes[k - 1] == 10 || bytes[k - 1] == 13;
    }

    static int IndexOfMarker(byte[] bytes, byte[] marker, int start) {
        for (int k = start; k <= bytes.Length - marker.Length; k++) {
            bool ok = true;
            for (int m = 0; m < marker.Length; m++) {
                if (bytes[k + m] != marker[m]) { ok = false; break; }
            }
            if (ok && IsCommandStart(bytes, k)) return k;
        }
        return -1;
    }

    public static ParseResult Parse(byte[] bytes) {
        var result = new ParseResult();
        string head = Encoding.ASCII.GetString(bytes, 0, Math.Min(512, bytes.Length));
        var sizeMatch = Regex.Match(head, @"SIZE\s+([\d.]+)\s*mm\s*,\s*([\d.]+)\s*mm", RegexOptions.IgnoreCase);
        if (sizeMatch.Success) {
            result.HasSize = true;
            result.WidthMm = double.Parse(sizeMatch.Groups[1].Value);
            result.HeightMm = double.Parse(sizeMatch.Groups[2].Value);
        }
        result.Bit0Prints = head.IndexOf("kcw_tspl_bit0_prints", StringComparison.OrdinalIgnoreCase) >= 0;

        var sb = new StringBuilder(bytes.Length);
        for (int i = 0; i < bytes.Length; i++) {
            byte x = bytes[i];
            if (x >= 32 && x <= 126) sb.Append((char)x);
            else if (x == 10 || x == 13) sb.Append((char)x);
            else sb.Append('.');
        }
        string clean = sb.ToString();
        foreach (Match pm in Regex.Matches(clean, @"(?m)^PRINT\s+([0-9]+)(?:\s*,\s*([0-9]+))?\s*$", RegexOptions.IgnoreCase)) {
            int sets = int.Parse(pm.Groups[1].Value);
            int copies = pm.Groups[2].Success ? int.Parse(pm.Groups[2].Value) : 1;
            result.PrintJobs.Add(new PrintJob { Sets = sets, Copies = copies, Raw = pm.Value.Trim() });
        }

        byte[] marker = Encoding.ASCII.GetBytes("BITMAP");
        int pos = 0;
        while (true) {
            int found = IndexOfMarker(bytes, marker, pos);
            if (found < 0) break;

            int hdrEnd = found + 6;
            while (hdrEnd < bytes.Length && (bytes[hdrEnd] == 32 || bytes[hdrEnd] == 9)) hdrEnd++;

            int commas = 0;
            while (hdrEnd < bytes.Length) {
                if (bytes[hdrEnd] == 44) {
                    commas++;
                    hdrEnd++;
                    if (commas == 5) break;
                    continue;
                }
                hdrEnd++;
            }
            if (commas < 5) break;

            string header = Encoding.ASCII.GetString(bytes, found, hdrEnd - found);
            var m = Regex.Match(header, @"BITMAP\s*(-?\d+)\s*,\s*(-?\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,", RegexOptions.IgnoreCase);
            if (!m.Success) { pos = found + 6; continue; }

            int x = int.Parse(m.Groups[1].Value);
            int y = int.Parse(m.Groups[2].Value);
            int widthBytes = int.Parse(m.Groups[3].Value);
            int height = int.Parse(m.Groups[4].Value);
            int dataLen = widthBytes * height;
            if (dataLen <= 0 || hdrEnd + dataLen > bytes.Length) { pos = found + 6; continue; }

            byte[] data = new byte[dataLen];
            Buffer.BlockCopy(bytes, hdrEnd, data, 0, dataLen);

            int idx = result.Bitmaps.Count;
            int sets = 1, copies = 1;
            if (idx < result.PrintJobs.Count) {
                sets = result.PrintJobs[idx].Sets;
                copies = result.PrintJobs[idx].Copies;
            }

            result.Bitmaps.Add(new BitmapPart {
                X = x, Y = y, WidthBytes = widthBytes, Height = height, Data = data,
                Sets = sets, Copies = copies
            });
            pos = hdrEnd + dataLen;
        }
        return result;
    }

    public static Bitmap RenderPart(BitmapPart b) {
        return RenderPart(b, false);
    }

    public static Bitmap RenderPart(BitmapPart b, bool bit0Prints) {
        int w = Math.Max(1, b.X + b.WidthBytes * 8);
        int h = Math.Max(1, b.Y + b.Height);
        var bmp = new Bitmap(w, h, PixelFormat.Format32bppArgb);
        using (var g = Graphics.FromImage(bmp)) g.Clear(Color.White);
        BlitMono(bmp, b, 0, 0, bit0Prints);
        return bmp;
    }

    static void BlitMono(Bitmap bmp, BitmapPart b, int offsetX, int offsetY) {
        BlitMono(bmp, b, offsetX, offsetY, false);
    }

    static void BlitMono(Bitmap bmp, BitmapPart b, int offsetX, int offsetY, bool bit0Prints) {
        var rect = new Rectangle(0, 0, bmp.Width, bmp.Height);
        var bd = bmp.LockBits(rect, ImageLockMode.ReadWrite, PixelFormat.Format32bppArgb);
        try {
            int stride = bd.Stride;
            byte[] pixels = new byte[Math.Abs(stride) * bmp.Height];
            Marshal.Copy(bd.Scan0, pixels, 0, pixels.Length);

            for (int row = 0; row < b.Height; row++) {
                int yy = offsetY + b.Y + row;
                if (yy < 0 || yy >= bmp.Height) continue;
                int rowOffset = row * b.WidthBytes;
                int destRow = yy * stride;
                for (int colByte = 0; colByte < b.WidthBytes; colByte++) {
                    byte byteVal = b.Data[rowOffset + colByte];
                    for (int bit = 0; bit < 8; bit++) {
                        bool on = (byteVal & (0x80 >> bit)) != 0;
                        if (bit0Prints) on = !on;
                        if (!on) continue;
                        int xx = offsetX + b.X + colByte * 8 + bit;
                        if (xx < 0 || xx >= bmp.Width) continue;
                        int idx = destRow + xx * 4;
                        pixels[idx] = 0;
                        pixels[idx + 1] = 0;
                        pixels[idx + 2] = 0;
                        pixels[idx + 3] = 255;
                    }
                }
            }
            Marshal.Copy(pixels, 0, bd.Scan0, pixels.Length);
        }
        finally {
            bmp.UnlockBits(bd);
        }
    }

    public static Bitmap Render(ParseResult parsed) {
        if (parsed == null || parsed.Bitmaps.Count == 0) return null;

        var parts = parsed.Bitmaps;
        const int gap = 16;
        const int headerH = 36;
        int cellW = 1, cellH = 1;
        foreach (var b in parts) {
            cellW = Math.Max(cellW, b.X + b.WidthBytes * 8);
            cellH = Math.Max(cellH, b.Y + b.Height);
        }

        int n = parts.Count;
        int totalW = n * cellW + (n - 1) * gap;
        int totalH = headerH + cellH;

        var bmp = new Bitmap(Math.Max(totalW, 1), Math.Max(totalH, 1), PixelFormat.Format32bppArgb);
        using (var g = Graphics.FromImage(bmp)) {
            g.Clear(Color.White);
            using (var font = new Font("Segoe UI", 9, FontStyle.Bold))
            using (var accent = new SolidBrush(Color.FromArgb(0, 90, 158))) {
                for (int i = 0; i < n; i++) {
                    int ox = i * (cellW + gap);
                    var b = parts[i];
                    string code = string.IsNullOrEmpty(b.Barcode) ? "(no barcode)" : b.Barcode;
                    string caption = string.Format("#{0}  {1}  x{2}", i + 1, code, b.PrintCount);
                    g.DrawString(caption, font, accent, ox, 8);
                    using (var pen = new Pen(Color.Gainsboro)) {
                        g.DrawRectangle(pen, ox, headerH, cellW - 1, cellH - 1);
                    }
                }
            }
        }

        for (int i = 0; i < n; i++) {
            int ox = i * (cellW + gap);
            BlitMono(bmp, parts[i], ox, headerH, parsed.Bit0Prints);
        }
        return bmp;
    }
}

public class RawPrinterHelper {
    [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Ansi)]
    public class DOCINFOA {
        [MarshalAs(UnmanagedType.LPStr)] public string pDocName;
        [MarshalAs(UnmanagedType.LPStr)] public string pOutputFile;
        [MarshalAs(UnmanagedType.LPStr)] public string pDataType;
    }

    [DllImport("winspool.Drv", EntryPoint = "OpenPrinterA", SetLastError = true,
        CharSet = CharSet.Ansi, ExactSpelling = true, CallingConvention = CallingConvention.StdCall)]
    public static extern bool OpenPrinter([MarshalAs(UnmanagedType.LPStr)] string szPrinter, out IntPtr hPrinter, IntPtr pd);

    [DllImport("winspool.Drv", EntryPoint = "ClosePrinter", SetLastError = true,
        ExactSpelling = true, CallingConvention = CallingConvention.StdCall)]
    public static extern bool ClosePrinter(IntPtr hPrinter);

    [DllImport("winspool.Drv", EntryPoint = "StartDocPrinterA", SetLastError = true,
        CharSet = CharSet.Ansi, ExactSpelling = true, CallingConvention = CallingConvention.StdCall)]
    public static extern bool StartDocPrinter(IntPtr hPrinter, int level, [In, MarshalAs(UnmanagedType.LPStruct)] DOCINFOA di);

    [DllImport("winspool.Drv", EntryPoint = "EndDocPrinter", SetLastError = true,
        ExactSpelling = true, CallingConvention = CallingConvention.StdCall)]
    public static extern bool EndDocPrinter(IntPtr hPrinter);

    [DllImport("winspool.Drv", EntryPoint = "StartPagePrinter", SetLastError = true,
        ExactSpelling = true, CallingConvention = CallingConvention.StdCall)]
    public static extern bool StartPagePrinter(IntPtr hPrinter);

    [DllImport("winspool.Drv", EntryPoint = "EndPagePrinter", SetLastError = true,
        ExactSpelling = true, CallingConvention = CallingConvention.StdCall)]
    public static extern bool EndPagePrinter(IntPtr hPrinter);

    [DllImport("winspool.Drv", EntryPoint = "WritePrinter", SetLastError = true,
        ExactSpelling = true, CallingConvention = CallingConvention.StdCall)]
    public static extern bool WritePrinter(IntPtr hPrinter, IntPtr pBytes, int dwCount, out int dwWritten);

    public static bool SendFileToPrinter(string printerName, string fileName) {
        IntPtr hPrinter;
        if (!OpenPrinter(printerName, out hPrinter, IntPtr.Zero))
            return false;

        var di = new DOCINFOA();
        di.pDocName = Path.GetFileName(fileName);
        di.pDataType = "RAW";

        try {
            if (!StartDocPrinter(hPrinter, 1, di)) return false;
            if (!StartPagePrinter(hPrinter)) return false;

            byte[] fileBytes = File.ReadAllBytes(fileName);
            IntPtr p = Marshal.AllocCoTaskMem(fileBytes.Length);
            Marshal.Copy(fileBytes, 0, p, fileBytes.Length);
            int written;
            bool ok = WritePrinter(hPrinter, p, fileBytes.Length, out written);
            Marshal.FreeCoTaskMem(p);

            EndPagePrinter(hPrinter);
            EndDocPrinter(hPrinter);
            return ok && written == fileBytes.Length;
        }
        finally {
            ClosePrinter(hPrinter);
        }
    }
}
"@

function Get-StickerBarcode {
    param($Part)
    if (-not $script:zxingOk) { return $null }
    $bmp = [PrnPreview]::RenderPart($Part)
    try {
        $reader = New-Object ZXing.BarcodeReader
        $reader.Options.TryHarder = $true
        $reader.AutoRotate = $true
        $reader.Options.PossibleFormats = [ZXing.BarcodeFormat[]]@(
            [ZXing.BarcodeFormat]::CODE_128,
            [ZXing.BarcodeFormat]::CODE_39,
            [ZXing.BarcodeFormat]::EAN_13,
            [ZXing.BarcodeFormat]::EAN_8,
            [ZXing.BarcodeFormat]::ITF,
            [ZXing.BarcodeFormat]::QR_CODE,
            [ZXing.BarcodeFormat]::UPC_A,
            [ZXing.BarcodeFormat]::UPC_E
        )
        $ls = New-Object ZXing.BitmapLuminanceSource $bmp
        $decoded = $reader.Decode($ls)
        if ($decoded) { return $decoded.Text }
        return $null
    }
    finally {
        $bmp.Dispose()
    }
}

$bytes = [System.IO.File]::ReadAllBytes($Path)
$parsed = [PrnPreview]::Parse($bytes)

# Decode barcode per sticker, then render (captions include barcode)
foreach ($part in $parsed.Bitmaps) {
    $code = Get-StickerBarcode -Part $part
    if ($code) { $part.Barcode = $code }
}

$preview = [PrnPreview]::Render($parsed)

$exclude = @('OneNote*', 'Microsoft Print to PDF', 'Microsoft XPS Document Writer', 'Fax', 'AnyDesk*')
$printers = @(Get-Printer | Where-Object {
    $name = $_.Name
    -not ($exclude | Where-Object { $name -like $_ })
} | Sort-Object Name)

if ($printers.Count -eq 0) {
    [System.Windows.Forms.MessageBox]::Show('No suitable printers found.', 'Print PRN', 'OK', 'Warning') | Out-Null
    if ($preview) { $preview.Dispose() }
    exit 1
}

$stickerCount = $parsed.Bitmaps.Count
$jobCount = $parsed.PrintJobs.Count
$totalLabels = $parsed.TotalLabels
if ($jobCount -eq 0 -and $stickerCount -gt 0) { $totalLabels = $stickerCount }

# Aggregate qty by barcode
$byBarcode = [ordered]@{}
$i = 0
foreach ($part in $parsed.Bitmaps) {
    $i++
    $key = if ($part.Barcode) { $part.Barcode } else { "(unread #$i)" }
    if (-not $byBarcode.Contains($key)) {
        $byBarcode[$key] = [pscustomobject]@{ Barcode = $key; Qty = 0; Jobs = @() }
    }
    $byBarcode[$key].Qty += $part.PrintCount
    $byBarcode[$key].Jobs += "#{0}({1}x{2})" -f $i, $part.Sets, $part.Copies
}

$form = New-Object System.Windows.Forms.Form
$form.Text = 'Print PRN - ' + [IO.Path]::GetFileName($Path)
$form.StartPosition = 'CenterScreen'
$form.MinimizeBox = $false
$form.MaximizeBox = $true
$form.ClientSize = New-Object System.Drawing.Size(980, 640)
$form.Font = New-Object System.Drawing.Font('Segoe UI', 9)
$form.BackColor = [System.Drawing.Color]::White

$info = New-Object System.Windows.Forms.Label
$info.Location = New-Object System.Drawing.Point(12, 8)
$info.Size = New-Object System.Drawing.Size(700, 40)
$line1 = [IO.Path]::GetFileName($Path)
if ($parsed.HasSize) { $line1 += "   |   $($parsed.WidthMm) x $($parsed.HeightMm) mm" }
if ($script:localPrnVersion) { $line1 += "   |   helper v$($script:localPrnVersion)" }
$line2 = "Stickers: $stickerCount   |   Jobs: $jobCount   |   Will print: $totalLabels label(s)"
$info.Text = "$line1`r`n$line2"

$updateLabel = $null
$topOffset = 0
if ($script:updateHint) {
    $updateLabel = New-Object System.Windows.Forms.Label
    $updateLabel.Location = New-Object System.Drawing.Point(12, 50)
    $updateLabel.Size = New-Object System.Drawing.Size(956, 22)
    $updateLabel.ForeColor = [System.Drawing.Color]::FromArgb(140, 80, 0)
    $updateLabel.Text = $script:updateHint
    $topOffset = 28
}

$list = New-Object System.Windows.Forms.ListView
$list.Location = New-Object System.Drawing.Point(720, (8 + $topOffset))
$list.Size = New-Object System.Drawing.Size(248, 150)
$list.View = 'Details'
$list.FullRowSelect = $true
$list.GridLines = $true
$list.HeaderStyle = 'Nonclickable'
[void]$list.Columns.Add('Barcode', 140)
[void]$list.Columns.Add('Qty', 50)
[void]$list.Columns.Add('Jobs', 50)
foreach ($row in $byBarcode.Values) {
    $item = New-Object System.Windows.Forms.ListViewItem($row.Barcode)
    [void]$item.SubItems.Add([string]$row.Qty)
    [void]$item.SubItems.Add(($row.Jobs -join ','))
    [void]$list.Items.Add($item)
}

$picture = New-Object System.Windows.Forms.PictureBox
$picture.Location = New-Object System.Drawing.Point(12, (168 + $topOffset))
$picture.Size = New-Object System.Drawing.Size(956, (380 - $topOffset))
$picture.SizeMode = 'Zoom'
$picture.BackColor = [System.Drawing.Color]::WhiteSmoke
$picture.BorderStyle = 'FixedSingle'
if ($preview) { $picture.Image = $preview }

$lblPrinter = New-Object System.Windows.Forms.Label
$lblPrinter.Text = 'Printer:'
$lblPrinter.AutoSize = $true
$lblPrinter.Location = New-Object System.Drawing.Point(12, 588)

$combo = New-Object System.Windows.Forms.ComboBox
$combo.DropDownStyle = 'DropDownList'
$combo.Location = New-Object System.Drawing.Point(70, 584)
$combo.Width = 520
foreach ($p in $printers) { [void]$combo.Items.Add($p.Name) }
$tsc = $printers | Where-Object { $_.Name -like 'TSC*' } | Select-Object -First 1
if ($tsc) { $combo.SelectedItem = $tsc.Name } else { $combo.SelectedIndex = 0 }

$btnPrint = New-Object System.Windows.Forms.Button
$btnPrint.Text = "Print ($totalLabels)"
$btnPrint.Size = New-Object System.Drawing.Size(110, 28)
$btnPrint.Location = New-Object System.Drawing.Point(740, 582)

$btnCancel = New-Object System.Windows.Forms.Button
$btnCancel.Text = 'Cancel'
$btnCancel.Size = New-Object System.Drawing.Size(90, 28)
$btnCancel.Location = New-Object System.Drawing.Point(860, 582)
$btnCancel.DialogResult = [System.Windows.Forms.DialogResult]::Cancel

$selectedPrinter = $null
$btnPrint.Add_Click({
    if ($combo.SelectedItem) {
        $script:selectedPrinter = [string]$combo.SelectedItem
        $form.DialogResult = [System.Windows.Forms.DialogResult]::OK
        $form.Close()
    }
})

$controls = New-Object System.Collections.Generic.List[System.Windows.Forms.Control]
[void]$controls.Add($info)
if ($updateLabel) { [void]$controls.Add($updateLabel) }
[void]$controls.Add($list)
[void]$controls.Add($picture)
[void]$controls.Add($lblPrinter)
[void]$controls.Add($combo)
[void]$controls.Add($btnPrint)
[void]$controls.Add($btnCancel)
$form.Controls.AddRange($controls.ToArray())
$form.AcceptButton = $btnPrint
$form.CancelButton = $btnCancel

$result = $form.ShowDialog()
$form.Dispose()
if ($preview) { $preview.Dispose() }

if ($result -ne [System.Windows.Forms.DialogResult]::OK -or -not $selectedPrinter) {
    exit 0
}

try {
    $ok = [RawPrinterHelper]::SendFileToPrinter($selectedPrinter, $Path)
    if (-not $ok) { throw "WritePrinter failed for '$selectedPrinter'." }
}
catch {
    [System.Windows.Forms.MessageBox]::Show(
        "Failed to send PRN to '$selectedPrinter'.`n`n$($_.Exception.Message)",
        'Print PRN', 'OK', 'Error'
    ) | Out-Null
    exit 1
}