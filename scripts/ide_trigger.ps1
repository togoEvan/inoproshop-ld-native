param(
    [Parameter(Mandatory=$true)][string]$ScriptPath,
    [int]$TimeoutSec = 90
)
$ErrorActionPreference = "Continue"

Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes

$uiaClient = [System.Windows.Automation.AutomationElement].Assembly.Location
$uiaTypes  = [System.Windows.Automation.AutomationElementIdentifiers].Assembly.Location

if (-not ("PlcUi" -as [type])) {
Add-Type -TypeDefinition @"
using System;
using System.Text;
using System.Threading;
using System.Collections.Generic;
using System.Runtime.InteropServices;
using System.Windows.Automation;

public class PlcUi {
    public delegate bool EnumProc(IntPtr h, IntPtr l);
    [DllImport("user32.dll")] public static extern bool EnumWindows(EnumProc cb, IntPtr l);
    [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
    [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
    [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern int GetClassName(IntPtr h, StringBuilder s, int n);
    [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern IntPtr FindWindowEx(IntPtr p, IntPtr a, string cls, string name);
    [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern IntPtr SendMessage(IntPtr h, uint m, IntPtr wp, string lp);
    [DllImport("user32.dll")] public static extern IntPtr SendMessage(IntPtr h, uint m, IntPtr wp, IntPtr lp);
    [DllImport("user32.dll")] public static extern IntPtr GetDlgItem(IntPtr h, int id);
    [DllImport("user32.dll")] public static extern bool PostMessage(IntPtr h, uint m, IntPtr wp, IntPtr lp);

    public static void InvokeAsync(AutomationElement el) {
        if (el == null) return;
        try {
            object pat = el.GetCurrentPattern(InvokePattern.Pattern);
            InvokePattern ip = (InvokePattern)pat;
            ThreadPool.QueueUserWorkItem(delegate(object _) {
                try { ip.Invoke(); } catch { }
            });
        } catch { }
    }

    public static AutomationElement FindByName(AutomationElement root, string name) {
        try {
            PropertyCondition c = new PropertyCondition(AutomationElement.NameProperty, name);
            return root.FindFirst(TreeScope.Descendants, c);
        } catch { return null; }
    }

    public static IntPtr FindDialog(uint pid) {
        IntPtr found = IntPtr.Zero;
        EnumWindows(delegate(IntPtr h, IntPtr l) {
            uint p; GetWindowThreadProcessId(h, out p);
            if (p == pid && IsWindowVisible(h)) {
                StringBuilder c = new StringBuilder(256);
                GetClassName(h, c, 256);
                if (c.ToString() == "#32770") { found = h; return false; }
            }
            return true;
        }, IntPtr.Zero);
        return found;
    }

    // 读取对话框内所有 Static 文本（用于捕获错误信息）
    public static string DialogText(IntPtr dlg) {
        StringBuilder sb = new StringBuilder();
        EnumChildWindows(dlg, delegate(IntPtr h, IntPtr l) {
            StringBuilder c = new StringBuilder(256);
            GetClassName(h, c, 256);
            if (c.ToString() == "Static") {
                StringBuilder t = new StringBuilder(2048);
                GetWindowText(h, t, 2048);
                if (t.Length > 0) sb.AppendLine(t.ToString());
            }
            return true;
        }, IntPtr.Zero);
        return sb.ToString();
    }

    [DllImport("user32.dll")] public static extern bool EnumChildWindows(IntPtr p, EnumProc cb, IntPtr l);
    [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern int GetWindowText(IntPtr h, StringBuilder s, int n);

    public static void CloseDialogs(uint pid) {
        List<IntPtr> ds = new List<IntPtr>();
        EnumWindows(delegate(IntPtr h, IntPtr l) {
            uint p; GetWindowThreadProcessId(h, out p);
            if (p == pid && IsWindowVisible(h)) {
                StringBuilder c = new StringBuilder(256);
                GetClassName(h, c, 256);
                if (c.ToString() == "#32770") { ds.Add(h); }
            }
            return true;
        }, IntPtr.Zero);
        foreach (IntPtr h in ds) {
            PostMessage(h, 0x0010, IntPtr.Zero, IntPtr.Zero);
        }
    }

    public static void CancelMenus(uint pid, IntPtr main) {
        List<IntPtr> pops = new List<IntPtr>();
        EnumWindows(delegate(IntPtr h, IntPtr l) {
            uint p; GetWindowThreadProcessId(h, out p);
            if (p == pid && IsWindowVisible(h) && h != main) {
                StringBuilder c = new StringBuilder(256);
                GetClassName(h, c, 256);
                string cn = c.ToString();
                if (cn != "#32770" && cn.IndexOf("WindowsForms10.Window") == 0) {
                    pops.Add(h);
                }
            }
            return true;
        }, IntPtr.Zero);
        foreach (IntPtr h in pops) {
            PostMessage(h, 0x0010, IntPtr.Zero, IntPtr.Zero);
        }
        PostMessage(main, 0x001F, IntPtr.Zero, IntPtr.Zero);
    }
}
"@ -ReferencedAssemblies $uiaClient, $uiaTypes
}

function Get-IdeWindow {
    foreach ($p in (Get-Process InoProShop -ErrorAction SilentlyContinue)) {
        if ($p.MainWindowHandle -ne 0 -and $p.MainWindowTitle -like "*InoProShop*") {
            return @{ Handle = $p.MainWindowHandle; Pid = $p.Id }
        }
    }
    return $null
}

$ide = Get-IdeWindow
if ($ide -eq $null) { Write-Output "FAIL: InoProShop not running"; exit 2 }
Write-Output ("IDE pid=" + $ide.Pid + " hwnd=" + $ide.Handle)

$main = [IntPtr]$ide.Handle
$pid32 = [uint32]$ide.Pid

[PlcUi]::CloseDialogs($pid32)
Start-Sleep -Milliseconds 700
[PlcUi]::CancelMenus($pid32, $main)
Start-Sleep -Milliseconds 700

$dlg = [IntPtr]::Zero
for ($attempt = 1; $attempt -le 3; $attempt++) {
    Write-Output ("--- attempt " + $attempt)

    $root = [System.Windows.Automation.AutomationElement]::FromHandle($main)
    $tools = [PlcUi]::FindByName($root, "Tools")
    if ($tools -eq $null) {
        Write-Output "  Tools not found"
        [PlcUi]::CancelMenus($pid32, $main)
        Start-Sleep -Milliseconds 900
        continue
    }
    [PlcUi]::InvokeAsync($tools)
    Start-Sleep -Milliseconds 900

    $root = [System.Windows.Automation.AutomationElement]::FromHandle($main)
    $sc = [PlcUi]::FindByName($root, "Scripting")
    if ($sc -eq $null) {
        Write-Output "  Scripting not found"
        [PlcUi]::CancelMenus($pid32, $main)
        Start-Sleep -Milliseconds 900
        continue
    }
    [PlcUi]::InvokeAsync($sc)
    Start-Sleep -Milliseconds 900

    $root = [System.Windows.Automation.AutomationElement]::FromHandle($main)
    $esf = [PlcUi]::FindByName($root, "Execute Script File...")
    if ($esf -eq $null) {
        Write-Output "  Execute Script File not found"
        [PlcUi]::CancelMenus($pid32, $main)
        Start-Sleep -Milliseconds 900
        continue
    }
    [PlcUi]::InvokeAsync($esf)

    for ($i = 0; $i -lt 40; $i++) {
        Start-Sleep -Milliseconds 200
        $dlg = [PlcUi]::FindDialog($pid32)
        if ($dlg -ne [IntPtr]::Zero) { break }
    }
    if ($dlg -ne [IntPtr]::Zero) { break }
    Write-Output "  dialog did not appear"
    [PlcUi]::CancelMenus($pid32, $main)
    Start-Sleep -Milliseconds 900
}

if ($dlg -eq [IntPtr]::Zero) {
    Write-Output "FAIL: file dialog not found after retries"
    exit 7
}
Write-Output ("dialog=" + $dlg)

$cbe = [IntPtr]::Zero
$cb = [IntPtr]::Zero
$edit = [IntPtr]::Zero
for ($i = 0; $i -lt 40; $i++) {
    $cbe = [PlcUi]::FindWindowEx($dlg, [IntPtr]::Zero, "ComboBoxEx32", $null)
    $cb  = [PlcUi]::FindWindowEx($cbe, [IntPtr]::Zero, "ComboBox", $null)
    $edit = [PlcUi]::FindWindowEx($cb, [IntPtr]::Zero, "Edit", $null)
    if ($edit -eq [IntPtr]::Zero) { $edit = [PlcUi]::FindWindowEx($dlg, [IntPtr]::Zero, "Edit", $null) }
    if ($edit -ne [IntPtr]::Zero) { break }
    Start-Sleep -Milliseconds 250
}
if ($edit -eq [IntPtr]::Zero) { Write-Output "FAIL: no edit"; exit 8 }

[void][PlcUi]::SendMessage($edit, 0x000C, [IntPtr]::Zero, $ScriptPath)
Start-Sleep -Milliseconds 400
$ok = [PlcUi]::GetDlgItem($dlg, 1)
if ($ok -eq [IntPtr]::Zero) { Write-Output "FAIL: no OK button"; exit 9 }
[void][PlcUi]::SendMessage($ok, 0x00F5, [IntPtr]::Zero, [IntPtr]::Zero)
Write-Output "OK clicked"

$deadline = (Get-Date).AddSeconds($TimeoutSec)
while ((Get-Date) -lt $deadline) {
    Start-Sleep -Milliseconds 200
    if (-not [PlcUi]::IsWindowVisible($dlg)) { break }
}
$closed = -not [PlcUi]::IsWindowVisible($dlg)
Write-Output ("dialog_closed=" + $closed)

[PlcUi]::CancelMenus($pid32, $main)
Start-Sleep -Milliseconds 300

if ($closed) { exit 0 } else { exit 10 }
