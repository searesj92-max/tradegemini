Set WshShell = CreateObject("WScript.Shell")
WshShell.Run """C:\Users\seares\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe"" -m hermes_cli.main gateway run", 0, False
