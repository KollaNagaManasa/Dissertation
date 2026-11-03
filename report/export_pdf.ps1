# Converts a .docx to PDF with Microsoft Word, updating every field first (table of contents,
# lists of figures/tables, page numbers, caption numbers) so the PDF never shows stale fields.
# Usage: powershell -File report/export_pdf.ps1 <input.docx> <output.pdf>
param([Parameter(Mandatory)][string]$InPath, [Parameter(Mandatory)][string]$OutPath)

$in = (Resolve-Path $InPath).Path
$out = [System.IO.Path]::GetFullPath($OutPath)
$word = New-Object -ComObject Word.Application
$word.Visible = $false
$word.DisplayAlerts = 0
try {
    $doc = $word.Documents.Open($in, $false, $false)
    $doc.Fields.Update() | Out-Null
    foreach ($toc in $doc.TablesOfContents) { $toc.Update() | Out-Null }
    $doc.Repaginate()
    foreach ($toc in $doc.TablesOfContents) { $toc.UpdatePageNumbers() | Out-Null }
    $doc.Save()
    $doc.ExportAsFixedFormat($out, 17)  # 17 = wdExportFormatPDF
    $doc.Close($false)
    Write-Output "wrote $out"
}
finally {
    $word.Quit()
}
