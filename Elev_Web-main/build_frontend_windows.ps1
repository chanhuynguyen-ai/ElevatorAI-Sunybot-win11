$frontend = "C:\elevator_ai\Elev_Web-main"
$backendDist = "C:\elevator_ai\ElevatorAI-Sunybot-v2\gui\web\dist"

Set-Location $frontend
npm install
npm run build

New-Item -ItemType Directory -Force -Path $backendDist | Out-Null
Copy-Item "$frontend\dist\*" $backendDist -Recurse -Force
Write-Host "Da build frontend moi va copy vao backend dist: $backendDist"
