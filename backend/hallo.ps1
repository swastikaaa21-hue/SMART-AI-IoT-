param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Args
)
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
Set-Location -LiteralPath $PSScriptRoot
& ".\venv\Scripts\python.exe" "test_chat_cli.py" @Args
