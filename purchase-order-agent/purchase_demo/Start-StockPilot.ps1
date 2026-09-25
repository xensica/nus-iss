$projectRoot = Split-Path -Parent $PSScriptRoot
$pythonPath = Join-Path $projectRoot '.venv\Scripts\python.exe'
& $pythonPath -m streamlit run (Join-Path $PSScriptRoot 'demo_app.py') --server.address 127.0.0.1 --server.port 8504 --server.headless true --browser.gatherUsageStats false --theme.base light --theme.primaryColor '#28785f' --theme.backgroundColor '#f6f8f6' --theme.secondaryBackgroundColor '#eef3ef' --theme.textColor '#21372f'
