Option Explicit
Dim WshShell, FSO, CurrentPath, PythonPath, ScriptPath

Set WshShell = CreateObject("WScript.Shell")
Set FSO = CreateObject("Scripting.FileSystemObject")

CurrentPath = FSO.GetParentFolderName(WScript.ScriptFullName)
WshShell.CurrentDirectory = CurrentPath

PythonPath = "venv\Scripts\pythonw.exe"
ScriptPath = "main.py"

If Not FSO.FileExists(PythonPath) Then
    MsgBox "Environment not ready." & vbCrLf & "Please double-click 'Setup.bat' first.", 48, "Todo Pro"
    WScript.Quit
End If

WshShell.Run Chr(34) & PythonPath & Chr(34) & " " & ScriptPath & " app", 0
Set WshShell = Nothing