' Launch Ark Server Manager at Windows logon (no browser popup).
Option Explicit
Dim sh, fso, scriptDir, ps1, cmd
Set sh = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
ps1 = scriptDir & "\Start-ArkManager.ps1"
' 1 = normal console window so updates/logs stay visible; False = do not wait.
cmd = "powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File """ & ps1 & """ -NoBrowser"
sh.Run cmd, 1, False
