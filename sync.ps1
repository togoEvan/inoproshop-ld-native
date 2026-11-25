# sync.ps1 — 一键同步：校验 CHANGELOG → commit → push
#
# 用法：
#   .\sync.ps1 -Message "fix: 修正 IN 引脚 Type 说明"
#   .\sync.ps1                      # 从 CHANGELOG 的 [Unreleased] 自动生成提交信息
#   .\sync.ps1 -DryRun              # 只检查，不提交
#
# 规则（见 AGENTS.md 第 5 节）：任何内容改动都必须更新 CHANGELOG 并推送。

[CmdletBinding()]
param(
    [string]$Message = "",
    [string]$Branch = "",
    [switch]$DryRun,
    [switch]$AllowEmptyChangelog
)

$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

function Fail($msg) {
    Write-Host "[FAIL] $msg" -ForegroundColor Red
    exit 1
}
function Info($msg) { Write-Host "[ .. ] $msg" -ForegroundColor Cyan }
function Ok($msg)   { Write-Host "[ OK ] $msg" -ForegroundColor Green }
function Warn($msg) { Write-Host "[WARN] $msg" -ForegroundColor Yellow }

# --- 0. 基本检查 -------------------------------------------------------------
if (-not (Test-Path ".git")) { Fail "当前目录不是 git 仓库：$PSScriptRoot" }
if (-not (Test-Path "CHANGELOG.md")) { Fail "缺少 CHANGELOG.md" }

$gitDir = (& git rev-parse --is-inside-work-tree 2>$null)
if ($gitDir -ne "true") { Fail "git 仓库状态异常" }

# --- 0.1 禁止任何交互弹窗 ----------------------------------------------------
# Git for Windows 的系统级配置是 credential.helper=helper-selector，
# 每次联网都会弹「选择凭据助手」的窗口。这里强制：
#   1) 仓库级用 wincred（纯命令行，直接从 Windows 凭据管理器读，零弹窗）
#   2) GIT_TERMINAL_PROMPT=0（终端也不许问）
#   3) GCM_INTERACTIVE=never（万一走到 GCM 也不许开浏览器/对话框）
$env:GIT_TERMINAL_PROMPT = "0"
$env:GCM_INTERACTIVE     = "never"

$currentHelper = (& git config --local --get-all credential.helper 2>$null) -join ","
if ($currentHelper -notmatch "wincred") {
    Info "配置仓库级凭据助手为 wincred（避免弹窗）"
    & git config --local --unset-all credential.helper 2>$null | Out-Null
    & git config --local --add credential.helper ""      | Out-Null  # 清掉系统级继承的 helper-selector
    & git config --local --add credential.helper wincred | Out-Null
    Ok "已设置 credential.helper=wincred"
}

if (-not $Branch) {
    $Branch = (& git rev-parse --abbrev-ref HEAD).Trim()
    if (-not $Branch) { Fail "无法确定当前分支" }
}
Info "当前分支：$Branch"

# --- 1. 是否有改动 -----------------------------------------------------------
$status = & git status --porcelain
if (-not $status) {
    Ok "工作区干净，没有需要同步的改动。"
    exit 0
}

Write-Host ""
Write-Host "改动文件：" -ForegroundColor White
$status | ForEach-Object { Write-Host "  $_" }
Write-Host ""

# --- 2. 校验 CHANGELOG 有变动 ------------------------------------------------
$changelogDirty = $status | Where-Object { $_ -match "CHANGELOG\.md" }
$unreleasedBody = ""
$changelogText = Get-Content "CHANGELOG.md" -Raw -Encoding UTF8
$m = [regex]::Match($changelogText, "(?ms)^##\s*\[Unreleased\](.*?)(?=^##\s*\[|\z)")
if ($m.Success) {
    $unreleasedBody = $m.Groups[1].Value.Trim()
}

if (-not $changelogDirty -and -not $AllowEmptyChangelog) {
    Write-Host "本次改动未包含 CHANGELOG.md。" -ForegroundColor Yellow
    Write-Host "按 AGENTS.md 第 5 节，任何内容改动都必须登记 CHANGELOG。" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "如果你确认这是纯格式/无意义改动，可加 -AllowEmptyChangelog 跳过。" -ForegroundColor Yellow
    Fail "拒绝提交：CHANGELOG.md 未更新"
}

if ($unreleasedBody -match "^###\s*(新增|修改|修复|文档)" -eq $false -and -not $unreleasedBody) {
    Warn "CHANGELOG 的 [Unreleased] 段落看起来是空的。"
}

# --- 3. 生成提交信息 ---------------------------------------------------------
if (-not $Message) {
    $firstBullet = [regex]::Match($unreleasedBody, "(?m)^\s*-\s+(.+)$")
    if ($firstBullet.Success) {
        $Message = $firstBullet.Groups[1].Value.Trim()
        # 粗略推断 type
        if ($unreleasedBody -match "###\s*修复") { $prefix = "fix" }
        elseif ($unreleasedBody -match "###\s*新增") { $prefix = "feat" }
        elseif ($unreleasedBody -match "###\s*文档") { $prefix = "docs" }
        else { $prefix = "chore" }
        if ($Message -notmatch "^(feat|fix|docs|refactor|test|chore)(\(.+\))?:") {
            $Message = "${prefix}: $Message"
        }
        Info "自动生成提交信息：$Message"
    } else {
        $Message = "chore: 同步更新 $(Get-Date -Format 'yyyy-MM-dd HH:mm')"
        Warn "无法从 CHANGELOG 提取条目，使用默认提交信息：$Message"
    }
}

# --- 4. 敏感信息扫描 ---------------------------------------------------------
$suspicious = $status | Where-Object {
    $_ -match "\.env$|token\.txt$|\.pem$|\.key$"
}
if ($suspicious) {
    Write-Host "检测到疑似凭据文件：" -ForegroundColor Red
    $suspicious | ForEach-Object { Write-Host "  $_" -ForegroundColor Red }
    Fail "拒绝提交：疑似凭据文件。请先确认已加入 .gitignore。"
}

# --- 5. DryRun 退出 ----------------------------------------------------------
if ($DryRun) {
    Ok "DryRun 模式：检查通过，未执行提交。"
    Write-Host "将执行：git add -A && git commit -m `"$Message`" && git push origin $Branch"
    exit 0
}

# --- 6. 提交并推送 -----------------------------------------------------------
Info "git add -A"
& git add -A
if ($LASTEXITCODE -ne 0) { Fail "git add 失败" }

Info "git commit"
& git commit -m $Message
if ($LASTEXITCODE -ne 0) { Fail "git commit 失败（可能没有实际改动）" }
Ok "已提交：$Message"

# --- 7. 推送 ----------------------------------------------------------------
$hasRemote = (& git remote) -contains "origin"
if (-not $hasRemote) {
    Warn "未配置 origin 远程，跳过推送。"
    Write-Host "配置方式：git remote add origin <仓库地址>" -ForegroundColor Yellow
    exit 0
}

Info "git push origin $Branch（最多重试 5 次，应对网络抖动）"
$pushed = $false
for ($i = 1; $i -le 5; $i++) {
    Write-Host "  尝试 $i / 5 ..." -NoNewline
    # git 把进度信息写到 stderr，PowerShell 会当成 ErrorRecord；先压成字符串再判断
    $prevEAP = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    $out = (& git push origin $Branch 2>&1 | ForEach-Object { "$_" }) -join "`n"
    $rc = $LASTEXITCODE
    $ErrorActionPreference = $prevEAP

    if ($rc -eq 0) {
        Write-Host " 成功" -ForegroundColor Green
        $pushed = $true
        break
    }
    Write-Host " 失败" -ForegroundColor Yellow
    ($out -split "`n" | Select-Object -Last 3) | ForEach-Object { Write-Host "    $_" -ForegroundColor DarkGray }

    if ($i -lt 5) {
        # 网络类错误：退避后重试；其他错误（如被拒绝）不重试
        if ($out -match "Could not connect|Failed to connect|Connection reset|timed out|unable to access|Could not resolve|Connection was reset") {
            Start-Sleep -Seconds (3 * $i)
        } elseif ($out -match "Authentication failed|terminal prompts disabled|could not read Username|403") {
            Write-Host ""
            Fail "凭据失效或不可用（已禁用交互，不会弹窗）。请在 Windows 凭据管理器里重新登录 GitHub，或手动 git push 一次完成登录。"
        } else {
            Write-Host ""
            Fail "推送失败（非网络原因，不重试）。请检查凭据或先 git pull --rebase。"
        }
    }
}
if (-not $pushed) {
    Fail "推送失败：已重试 5 次仍连不上 github.com。检查网络后重新运行本脚本（本地提交已完成，不会丢）。"
}

Ok "pushed to origin/$Branch"
Write-Host ""
Write-Host "同步完成。" -ForegroundColor Green
