Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass

$root = "C:\Projektit\invoice-app"
Set-Location $root

Start-Process powershell -ArgumentList "-NoExit", "-Command", "$root\scripts\start_api.ps1"
Start-Sleep -Seconds 1

Set-Location "$root\frontend"
npm run dev
