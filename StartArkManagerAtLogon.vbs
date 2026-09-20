' Starts Ark Server Manager at Windows logon (minimized, no browser).
' Prefer the Startup entry managed by Start-ArkManager.ps1 / server.mjs.
Option Explicit
Dim sh, fso, scriptDir, ps1, cmd
Set sh = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
ps1 = scriptDir & "\Start-ArkManager.ps1"
If Not fso.FileExists(ps1) Then WScript.Quit 1
' 7 = minimized; False = do not wait.
cmd = "powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File """ & ps1 & """ -NoBrowser"
sh.Run cmd, 7, False
