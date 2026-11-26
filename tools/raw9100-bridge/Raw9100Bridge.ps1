# KCW raw TCP :9100 -> Windows spooler (USB TSC on KSS-PC)
param(
    [string]$PrinterName = "TSC TTP-244 Pro",
    [int]$Port = 9100,
    [string]$LogPath = "C:\KCW\raw9100\bridge.log"
)

$ErrorActionPreference = "Stop"

function Write-BridgeLog([string]$Message) {
    $line = "[{0}] {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $Message
    Add-Content -Path $LogPath -Value $line -Encoding UTF8
    Write-Host $line
}

Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;

public class RawPrinterHelper9100 {
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

    public static bool SendBytesToPrinter(string printerName, byte[] bytes, string docName) {
        IntPtr hPrinter;
        if (!OpenPrinter(printerName, out hPrinter, IntPtr.Zero)) return false;
        var di = new DOCINFOA();
        di.pDocName = docName;
        di.pDataType = "RAW";
        try {
            if (!StartDocPrinter(hPrinter, 1, di)) return false;
            if (!StartPagePrinter(hPrinter)) return false;
            IntPtr p = Marshal.AllocCoTaskMem(bytes.Length);
            Marshal.Copy(bytes, 0, p, bytes.Length);
            int written;
            bool ok = WritePrinter(hPrinter, p, bytes.Length, out written);
            Marshal.FreeCoTaskMem(p);
            EndPagePrinter(hPrinter);
            EndDocPrinter(hPrinter);
            return ok && written == bytes.Length;
        }
        finally { ClosePrinter(hPrinter); }
    }
}
"@

function Send-RawToPrinter([byte[]]$Bytes) {
    if (-not $Bytes -or $Bytes.Length -eq 0) { return }
    $ok = [RawPrinterHelper9100]::SendBytesToPrinter($PrinterName, $Bytes, "KCW-raw9100")
    if (-not $ok) {
        $err = [Runtime.InteropServices.Marshal]::GetLastWin32Error()
        throw "WritePrinter failed for '$PrinterName' (Win32=$err)"
    }
}

function Read-AllBytes([System.Net.Sockets.NetworkStream]$Stream, [int]$IdleMs = 300) {
    $ms = New-Object System.IO.MemoryStream
    $buf = New-Object byte[] 8192
    $Stream.ReadTimeout = 2000
    while ($true) {
        try {
            $n = $Stream.Read($buf, 0, $buf.Length)
        } catch [System.IO.IOException] {
            break
        }
        if ($n -le 0) { break }
        $ms.Write($buf, 0, $n)
        $idle = 0
        while (-not $Stream.DataAvailable -and $idle -lt $IdleMs) {
            Start-Sleep -Milliseconds 50
            $idle += 50
        }
        if (-not $Stream.DataAvailable) { break }
    }
    return $ms.ToArray()
}

New-Item -ItemType Directory -Force -Path (Split-Path $LogPath) | Out-Null
$listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Any, $Port)
$listener.Start()
Write-BridgeLog "Listening 0.0.0.0:$Port -> '$PrinterName'"

while ($true) {
    $client = $null
    try {
        $client = $listener.AcceptTcpClient()
        $remote = $client.Client.RemoteEndPoint.ToString()
        $stream = $client.GetStream()
        $payload = Read-AllBytes $stream
        if ($payload.Length -gt 0) {
            Send-RawToPrinter $payload
            Write-BridgeLog ("printed {0} bytes from {1}" -f $payload.Length, $remote)
        } else {
            Write-BridgeLog ("empty payload from {0}" -f $remote)
        }
    }
    catch {
        Write-BridgeLog ("error: {0}" -f $_)
    }
    finally {
        if ($client) { try { $client.Close() } catch {} }
    }
}
