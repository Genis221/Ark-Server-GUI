' Starts Ark Server Manager at Windows logon via CMD (silent, no browser).
' Prefer the Startup entry managed by Start-ArkManager.ps1 / server.mjs.
Option Explicit
Dim sh, fso, scriptDir, launcher, dataDir, logFile, cmd, rc
Set sh = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
launcher = scriptDir & "\Start Ark Manager.cmd"
If Not fso.FileExists(launcher) Then WScript.Quit 1

dataDir = scriptDir & "\data"
On Error Resume Next
If Not fso.FolderExists(dataDir) Then fso.CreateFolder dataDir
On Error GoTo 0
logFile = dataDir & "\logon-start.log"

' Give the desktop / profile a moment after sign-in.
WScript.Sleep 8000

' Nested quotes so "silent" is an argument to the .cmd, not to cmd.exe.
' Window style 1 = normal (hidden PowerShell still runs via silent mode).
cmd = "cmd.exe /c """"" & launcher & """ silent"""
rc = sh.Run(cmd, 1, False)

On Error Resume Next
Dim ts
Set ts = fso.OpenTextFile(logFile, 8, True)
ts.WriteLine Now & " launched Start Ark Manager.cmd silent (async start code=" & rc & ")"
ts.Close
On Error GoTo 0
