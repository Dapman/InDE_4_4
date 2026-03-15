# InDE Build Harness - Test Runner (PowerShell)
# Runs all tests with proper Python path configuration

param(
    [switch]$Verbose,
    [switch]$Coverage,
    [string]$Filter
)

Write-Host "============================================================"
Write-Host "InDE v3.7.0 Test Runner"
Write-Host "============================================================"
Write-Host ""

# Get script directory
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectDir = Split-Path -Parent $ScriptDir

# Set Python path
$env:PYTHONPATH = "$ProjectDir\app;$ProjectDir;$env:PYTHONPATH"

# Change to project directory
Set-Location $ProjectDir

# Check for pytest
$pytestPath = Get-Command pytest -ErrorAction SilentlyContinue
if (-not $pytestPath) {
    Write-Host "Error: pytest not found. Install with: pip install pytest" -ForegroundColor Red
    exit 1
}

Write-Host "Project directory: $ProjectDir"
Write-Host "Python path includes: app\"
Write-Host ""

# Build pytest arguments
$pytestArgs = @()
if ($Verbose) { $pytestArgs += "-v" }
if ($Coverage) { $pytestArgs += "--cov=app", "--cov-report=term-missing" }
if ($Filter) { $pytestArgs += "-k", $Filter }

$TotalPassed = 0
$TotalFailed = 0

function Run-TestSuite {
    param($SuiteName, $TestPath)

    if (Test-Path $TestPath) {
        Write-Host "[$SuiteName]" -ForegroundColor Yellow
        Write-Host "Running: pytest $TestPath $($pytestArgs -join ' ')"

        $result = & pytest $TestPath @pytestArgs
        if ($LASTEXITCODE -eq 0) {
            Write-Host "PASSED" -ForegroundColor Green
            $script:TotalPassed++
        } else {
            Write-Host "FAILED" -ForegroundColor Red
            $script:TotalFailed++
        }
        Write-Host ""
    } else {
        Write-Host "[$SuiteName] - Skipped (not found: $TestPath)" -ForegroundColor Yellow
        Write-Host ""
    }
}

# Run test suites
Run-TestSuite "v3.7.0 Display Labels" "tests\test_display_labels.py"
Run-TestSuite "v3.7.0 Response Transform" "tests\test_response_transform.py"
Run-TestSuite "v3.4 Session 1" "tests\test_v34_session1.py"
Run-TestSuite "v3.4 Session 2" "tests\test_v34_session2.py"
Run-TestSuite "Build Verification" "app\tests\test_build_verification.py"
Run-TestSuite "Backward Compatibility" "app\tests\test_backward_compat.py"
Run-TestSuite "Events v3.2" "app\tests\test_events_v32.py"
Run-TestSuite "IKF Tests" "app\tests\test_ikf.py"
Run-TestSuite "Intelligence Tests" "app\tests\test_intelligence.py"
Run-TestSuite "Portfolio Tests" "app\tests\test_portfolio.py"
Run-TestSuite "TIM Tests" "app\tests\test_tim.py"
Run-TestSuite "SILR Enrichment" "app\tests\test_silr_enrichment.py"
Run-TestSuite "Teams v3.3" "app\tests\test_v33_teams.py"
Run-TestSuite "IKF Service" "ikf-service\tests\"

# Summary
Write-Host "============================================================"
Write-Host "Test Summary"
Write-Host "============================================================"
Write-Host "Passed: $TotalPassed" -ForegroundColor Green
Write-Host "Failed: $TotalFailed" -ForegroundColor Red
Write-Host ""

if ($TotalFailed -gt 0) {
    Write-Host "Some tests failed!" -ForegroundColor Red
    exit 1
} else {
    Write-Host "All tests passed!" -ForegroundColor Green
    exit 0
}
