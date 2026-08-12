Set WshShell = CreateObject("WScript.Shell")
Set FSO = CreateObject("Scripting.FileSystemObject")

ScriptDir = FSO.GetParentFolderName(WScript.ScriptFullName)
Ps1Path = ScriptDir & "\start_stock_check_detached.ps1"

' Must go through Task Scheduler. Plain WshShell.Run stays inside the OpenSSH
' session job and is killed when you disconnect, even with window style 0.
cmd = "powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File """ & Ps1Path & """"
WshShell.Run cmd, 0, True
