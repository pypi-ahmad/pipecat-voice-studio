[CmdletBinding()]
param(
    [switch]$WithApi,
    [switch]$SetupOnly,
    [ValidateRange(1, 65535)][int]$WorkerPort = 7860,
    [ValidateRange(1, 65535)][int]$StreamlitPort = 8501,
    [ValidateRange(1, 65535)][int]$ApiPort = 8000,
    [ValidateRange(1, 65535)][int]$GatewayPort = 8080
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$ProjectRoot = $PSScriptRoot
$PrimaryPython = "3.14.7"
$FallbackPython = "3.13.13"
$WorkerProcess = $null
$ApiProcess = $null
$GatewayProcess = $null
$CalendarProcess = $null

Set-Location -LiteralPath $ProjectRoot

function Resolve-Uv {
    $command = Get-Command uv -ErrorAction SilentlyContinue
    if ($null -ne $command) {
        return $command.Source
    }

    Write-Host "uv was not found. Installing it with the official installer..."
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -Command `
        "irm https://astral.sh/uv/install.ps1 | iex"
    if ($LASTEXITCODE -ne 0) {
        throw "The uv installer failed with exit code $LASTEXITCODE."
    }

    $candidates = @(
        (Join-Path $HOME ".local\bin\uv.exe"),
        (Join-Path $HOME ".cargo\bin\uv.exe")
    )
    foreach ($candidate in $candidates) {
        if (Test-Path -LiteralPath $candidate) {
            return $candidate
        }
    }

    $command = Get-Command uv -ErrorAction SilentlyContinue
    if ($null -eq $command) {
        throw "uv was installed but could not be located. Open a new terminal and run this launcher again."
    }
    return $command.Source
}

function Invoke-Uv {
    & $script:UvExe @args
    if ($LASTEXITCODE -ne 0) {
        throw "uv $($args -join ' ') failed with exit code $LASTEXITCODE."
    }
}

function Test-PortAvailable([int]$Port) {
    $listener = [System.Net.Sockets.TcpListener]::new(
        [System.Net.IPAddress]::Loopback,
        $Port
    )
    try {
        $listener.Start()
        return $true
    }
    catch [System.Net.Sockets.SocketException] {
        return $false
    }
    finally {
        $listener.Stop()
    }
}

function Wait-ForEndpoint(
    [string]$Url,
    [System.Diagnostics.Process]$Process,
    [string]$ServiceName,
    [int]$TimeoutSeconds = 30
) {
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    do {
        if ($Process.HasExited) {
            throw "$ServiceName exited before it became ready."
        }
        try {
            $null = Invoke-RestMethod -Uri $Url -TimeoutSec 1
            return
        }
        catch {
            Start-Sleep -Milliseconds 500
        }
    } while ((Get-Date) -lt $deadline)

    throw "$ServiceName did not become ready within $TimeoutSeconds seconds."
}

function Stop-OwnedProcess([System.Diagnostics.Process]$Process) {
    if ($null -eq $Process -or $Process.HasExited) {
        return
    }
    & taskkill.exe /PID $Process.Id /T /F *> $null
    if ($LASTEXITCODE -ne 0 -and -not $Process.HasExited) {
        Stop-Process -Id $Process.Id -Force -ErrorAction SilentlyContinue
    }
    $Process.WaitForExit(5000) | Out-Null
}

function Show-LogTail([string]$Path) {
    if (Test-Path -LiteralPath $Path) {
        Get-Content -LiteralPath $Path -Tail 40
    }
}

if (-not [Environment]::Is64BitOperatingSystem) {
    throw "Pipecat Voice Studio requires 64-bit Windows."
}

$script:UvExe = Resolve-Uv
Write-Host "Using uv: $script:UvExe"

& $script:UvExe python find $PrimaryPython *> $null
if ($LASTEXITCODE -eq 0) {
    $PythonVersion = $PrimaryPython
}
else {
    & $script:UvExe python install $PrimaryPython
    if ($LASTEXITCODE -eq 0) {
        $PythonVersion = $PrimaryPython
    }
    else {
        Write-Warning "Python $PrimaryPython could not be installed; trying $FallbackPython."
        & $script:UvExe python find $FallbackPython *> $null
        if ($LASTEXITCODE -ne 0) {
            Invoke-Uv python install $FallbackPython
        }
        $PythonVersion = $FallbackPython
    }
}

if (-not (Test-Path -LiteralPath ".venv")) {
    Invoke-Uv venv --python $PythonVersion .venv
}

& $script:UvExe sync --check --python $PythonVersion
if ($LASTEXITCODE -ne 0) {
    Invoke-Uv sync --locked --python $PythonVersion
}

$PythonExe = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $PythonExe)) {
    throw "The project virtual environment was not created at .venv."
}
& $PythonExe -c "import dateutil, pandas" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Repairing the python-dateutil installation..."
    Invoke-Uv sync --locked --python $PythonVersion --reinstall-package python-dateutil
    & $PythonExe -c "import dateutil, pandas"
    if ($LASTEXITCODE -ne 0) {
        throw "Python dependency verification failed after repairing python-dateutil."
    }
}

if (-not (Test-Path -LiteralPath ".env")) {
    Copy-Item -LiteralPath ".env.example" -Destination ".env"
    Write-Host "Created .env from .env.example."
}

if ([string]::IsNullOrWhiteSpace($env:OPENAI_API_KEY)) {
    $UserApiKey = [Environment]::GetEnvironmentVariable("OPENAI_API_KEY", "User")
    if (-not [string]::IsNullOrWhiteSpace($UserApiKey)) {
        $env:OPENAI_API_KEY = $UserApiKey
    }
}
if ([string]::IsNullOrWhiteSpace($env:OPENAI_BASE_URL)) {
    $UserBaseUrl = [Environment]::GetEnvironmentVariable("OPENAI_BASE_URL", "User")
    if (-not [string]::IsNullOrWhiteSpace($UserBaseUrl)) {
        $env:OPENAI_BASE_URL = $UserBaseUrl
    }
}

$HasApiKey = Select-String -LiteralPath ".env" `
    -Pattern '^\s*OPENAI_API_KEY\s*=\s*[^\s#].*$' -Quiet
if (-not $HasApiKey -and [string]::IsNullOrWhiteSpace($env:OPENAI_API_KEY)) {
    Write-Warning "OPENAI_API_KEY is empty. The studio will open, but live voice and evaluations require a key."
}

$FrontendBuild = Join-Path $ProjectRoot "src\pipecat_voice_studio\ui\frontend\build"
$JavaScriptAssets = @(Get-ChildItem -LiteralPath $FrontendBuild -Filter "index-*.js" `
    -File -ErrorAction SilentlyContinue)
$CssAssets = @(Get-ChildItem -LiteralPath $FrontendBuild -Filter "index-*.css" `
    -File -ErrorAction SilentlyContinue)
if ($JavaScriptAssets.Count -ne 1 -or $CssAssets.Count -ne 1) {
    if ($null -eq (Get-Command npm -ErrorAction SilentlyContinue)) {
        throw "Frontend assets are missing. Install Node.js/npm, then run this launcher again."
    }
    Write-Host "Building missing frontend assets..."
    Push-Location "src\pipecat_voice_studio\ui\frontend"
    try {
        & npm ci
        if ($LASTEXITCODE -ne 0) { throw "npm ci failed." }
        & npm run build
        if ($LASTEXITCODE -ne 0) { throw "npm run build failed." }
    }
    finally {
        Pop-Location
    }
}

if ($SetupOnly) {
    Write-Host "Setup complete. Virtual environment: $PythonExe"
    exit 0
}

$Ports = @($WorkerPort, $StreamlitPort, $GatewayPort)
if ($WithApi) { $Ports += $ApiPort }
if (($Ports | Sort-Object -Unique).Count -ne $Ports.Count) {
    throw "Worker, Streamlit, and API ports must be distinct."
}
foreach ($port in $Ports) {
    if (-not (Test-PortAvailable $port)) {
        throw "Port $port is already in use. Stop the existing service or select another port."
    }
}

$env:PVS_BOT_BASE_URL = "http://127.0.0.1:$WorkerPort"
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
$LogDirectory = Join-Path $ProjectRoot "artifacts\launcher"
New-Item -ItemType Directory -Path $LogDirectory -Force | Out-Null
$WorkerOutLog = Join-Path $LogDirectory "worker.out.log"
$WorkerErrorLog = Join-Path $LogDirectory "worker.err.log"
$ApiOutLog = Join-Path $LogDirectory "api.out.log"
$ApiErrorLog = Join-Path $LogDirectory "api.err.log"
$GatewayOutLog = Join-Path $LogDirectory "gateway.out.log"
$GatewayErrorLog = Join-Path $LogDirectory "gateway.err.log"
$CalendarOutLog = Join-Path $LogDirectory "calendar.out.log"
$CalendarErrorLog = Join-Path $LogDirectory "calendar.err.log"

try {
    $WorkerArguments = @(
        "-m", "pipecat_voice_studio.voice.bot",
        "--host", "127.0.0.1",
        "--port", "$WorkerPort",
        "--allowed-origins",
        "http://localhost:$StreamlitPort",
        "http://127.0.0.1:$StreamlitPort"
    )
    $WorkerProcess = Start-Process -FilePath $PythonExe -ArgumentList $WorkerArguments `
        -PassThru -WindowStyle Hidden `
        -RedirectStandardOutput $WorkerOutLog -RedirectStandardError $WorkerErrorLog
    Write-Host "Starting Pipecat worker on http://127.0.0.1:$WorkerPort ..."
    try {
        Wait-ForEndpoint "http://127.0.0.1:$WorkerPort/status" $WorkerProcess "Pipecat worker"
    }
    catch {
        Show-LogTail $WorkerOutLog
        Show-LogTail $WorkerErrorLog
        throw
    }
    Write-Host "Pipecat worker is ready."

    $GatewayArguments = @(
        "-m", "uvicorn", "pipecat_voice_studio.telephony_gateway:app",
        "--host", "127.0.0.1", "--port", "$GatewayPort",
        "--proxy-headers", "--forwarded-allow-ips", "127.0.0.1"
    )
    $GatewayProcess = Start-Process -FilePath $PythonExe -ArgumentList $GatewayArguments `
        -PassThru -WindowStyle Hidden `
        -RedirectStandardOutput $GatewayOutLog -RedirectStandardError $GatewayErrorLog
    try {
        Wait-ForEndpoint "http://127.0.0.1:$GatewayPort/health" $GatewayProcess "Telephony gateway"
    }
    catch {
        Show-LogTail $GatewayOutLog
        Show-LogTail $GatewayErrorLog
        throw
    }
    Write-Host "Telephony callback gateway: http://127.0.0.1:$GatewayPort"

    $CalendarEnabled = & $PythonExe -c `
        "from pipecat_voice_studio.config import get_settings; s=get_settings(); print(int(bool(s.google_service_account_json and s.google_calendar_id)))"
    if ($CalendarEnabled -eq "1") {
        $CalendarProcess = Start-Process -FilePath $PythonExe `
            -ArgumentList @("-m", "pipecat_voice_studio.calendar_worker") `
            -PassThru -WindowStyle Hidden `
            -RedirectStandardOutput $CalendarOutLog -RedirectStandardError $CalendarErrorLog
        Write-Host "Google Calendar synchronization worker started."
    }

    if ($WithApi) {
        $ApiArguments = @(
            "-m", "uvicorn", "pipecat_voice_studio.api.app:app",
            "--host", "127.0.0.1", "--port", "$ApiPort"
        )
        $ApiProcess = Start-Process -FilePath $PythonExe -ArgumentList $ApiArguments `
            -PassThru -WindowStyle Hidden `
            -RedirectStandardOutput $ApiOutLog -RedirectStandardError $ApiErrorLog
        try {
            Wait-ForEndpoint "http://127.0.0.1:$ApiPort/health" $ApiProcess "Management API"
        }
        catch {
            Show-LogTail $ApiOutLog
            Show-LogTail $ApiErrorLog
            throw
        }
        Write-Host "Management API: http://127.0.0.1:$ApiPort/docs"
    }

    Write-Host "Opening Streamlit at http://127.0.0.1:$StreamlitPort"
    & $PythonExe -m streamlit run `
        "src\pipecat_voice_studio\ui\streamlit_app.py" `
        --server.address 127.0.0.1 `
        --server.port $StreamlitPort
    if ($LASTEXITCODE -ne 0) {
        throw "Streamlit exited with code $LASTEXITCODE."
    }
}
finally {
    Stop-OwnedProcess $CalendarProcess
    Stop-OwnedProcess $GatewayProcess
    Stop-OwnedProcess $ApiProcess
    Stop-OwnedProcess $WorkerProcess
}
