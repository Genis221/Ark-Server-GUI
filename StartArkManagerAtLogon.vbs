' Starts Ark Server Manager at Windows logon via CMD (silent, no browser).
Option Explicit
Dim sh, fso, scriptDir, launcher, cmd
Set sh = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
launcher = scriptDir & "\Start Ark Manager.cmd"
If Not fso.FileExists(launcher) Then WScript.Quit 1
' 0 = hidden window; False = do not wait.
cmd = "cmd.exe /c """ & launcher & """ silent"
sh.Run cmd, 0, False
