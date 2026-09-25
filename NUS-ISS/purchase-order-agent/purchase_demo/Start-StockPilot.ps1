$projectRoot = Split-Path -Parent $PSScriptRoot
$pythonPath = Join-Path $projectRoot '.venv\Scripts\python.exe'
& $pythonPath -m streamlit run (Join-Path $PSScriptRoot 'demo_app.py') --server.address 127.0.0.1 --server.port 8504 --server.headless true --browser.gatherUsageStats false --theme.base light --theme.primaryColor '#e95827' --theme.backgroundColor '#f5f4ee' --theme.secondaryBackgroundColor '#fffefa' --theme.textColor '#22231f'
