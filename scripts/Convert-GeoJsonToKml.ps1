<#
.SYNOPSIS
    Converts data_processed/mandalay_townships.geojson to data_processed/mandalay_townships.kml.

.DESCRIPTION
    Reads a GeoJSON FeatureCollection of Mandalay township polygons and produces a
    valid KML 2.2 document.  Each GeoJSON Feature becomes one <Placemark>:

      adm3_name  → <name>
      adm3_name1, adm3_pcode, adm2_name, area_sqkm, center_lat, center_lon
                 → <ExtendedData> / <Data> elements
      geometry   → <Polygon><outerBoundaryIs><LinearRing><coordinates>
                   (GeoJSON lon,lat pairs are written as KML "lon,lat,0 " tuples)

.EXAMPLE
    pwsh -File scripts/Convert-GeoJsonToKml.ps1
#>

[CmdletBinding()]
param (
    [string]$InputPath  = (Join-Path $PSScriptRoot '..' 'data_processed' 'mandalay_townships.geojson'),
    [string]$OutputPath = (Join-Path $PSScriptRoot '..' 'data_processed' 'mandalay_townships.kml')
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# ---------------------------------------------------------------------------
# 1. Read and parse the GeoJSON file
# ---------------------------------------------------------------------------
$InputPath  = [System.IO.Path]::GetFullPath($InputPath)
$OutputPath = [System.IO.Path]::GetFullPath($OutputPath)

if (-not (Test-Path $InputPath)) {
    throw "Input file not found: $InputPath"
}

Write-Host "Reading $InputPath …"
$geojson = Get-Content -Raw -Path $InputPath | ConvertFrom-Json

if ($geojson.type -ne 'FeatureCollection') {
    throw "Expected a GeoJSON FeatureCollection, got: $($geojson.type)"
}

# ---------------------------------------------------------------------------
# 2. Helper: convert a single coordinate ring to KML <coordinates> text
#    GeoJSON ring: array of [lon, lat] pairs
#    KML format  : "lon,lat,0 lon,lat,0 …"
# ---------------------------------------------------------------------------
function ConvertRingToKmlCoords ([array]$ring) {
    $parts = foreach ($pt in $ring) {
        "$($pt[0]),$($pt[1]),0"
    }
    return ($parts -join ' ')
}

# ---------------------------------------------------------------------------
# 3. Helper: XML-escape a string value
# ---------------------------------------------------------------------------
function XmlEscape ([string]$text) {
    return [System.Security.SecurityElement]::Escape($text)
}

# ---------------------------------------------------------------------------
# 4. Build the KML document as a string
# ---------------------------------------------------------------------------
$sb = [System.Text.StringBuilder]::new()

$null = $sb.AppendLine('<?xml version="1.0" encoding="UTF-8"?>')
$null = $sb.AppendLine('<kml xmlns="http://www.opengis.net/kml/2.2">')
$null = $sb.AppendLine('  <Document>')
$null = $sb.AppendLine('    <name>Mandalay Townships</name>')

foreach ($feature in $geojson.features) {

    $props = $feature.properties
    $geom  = $feature.geometry

    if ($geom.type -ne 'Polygon') {
        Write-Warning "Skipping feature with geometry type '$($geom.type)' (expected Polygon)"
        continue
    }

    $name        = XmlEscape ($props.adm3_name)
    $name1       = XmlEscape ($props.adm3_name1)
    $pcode       = XmlEscape ($props.adm3_pcode)
    $adm2        = XmlEscape ($props.adm2_name)
    $areaSqkm    = $props.area_sqkm
    $centerLat   = $props.center_lat
    $centerLon   = $props.center_lon

    # --- outer ring (index 0) -----------------------------------------------
    $outerCoords = ConvertRingToKmlCoords $geom.coordinates[0]

    # --- inner rings (holes, indices 1…n) ------------------------------------
    $innerRingsXml = [System.Text.StringBuilder]::new()
    for ($i = 1; $i -lt $geom.coordinates.Count; $i++) {
        $innerCoords = ConvertRingToKmlCoords $geom.coordinates[$i]
        $null = $innerRingsXml.AppendLine("        <innerBoundaryIs>")
        $null = $innerRingsXml.AppendLine("          <LinearRing>")
        $null = $innerRingsXml.AppendLine("            <coordinates>$innerCoords</coordinates>")
        $null = $innerRingsXml.AppendLine("          </LinearRing>")
        $null = $innerRingsXml.AppendLine("        </innerBoundaryIs>")
    }

    $null = $sb.AppendLine('    <Placemark>')
    $null = $sb.AppendLine("      <name>$name</name>")
    $null = $sb.AppendLine('      <ExtendedData>')
    $null = $sb.AppendLine("        <Data name=""adm3_name1""><value>$name1</value></Data>")
    $null = $sb.AppendLine("        <Data name=""adm3_pcode""><value>$pcode</value></Data>")
    $null = $sb.AppendLine("        <Data name=""adm2_name""><value>$adm2</value></Data>")
    $null = $sb.AppendLine("        <Data name=""area_sqkm""><value>$areaSqkm</value></Data>")
    $null = $sb.AppendLine("        <Data name=""center_lat""><value>$centerLat</value></Data>")
    $null = $sb.AppendLine("        <Data name=""center_lon""><value>$centerLon</value></Data>")
    $null = $sb.AppendLine('      </ExtendedData>')
    $null = $sb.AppendLine('      <Polygon>')
    $null = $sb.AppendLine('        <outerBoundaryIs>')
    $null = $sb.AppendLine('          <LinearRing>')
    $null = $sb.AppendLine("            <coordinates>$outerCoords</coordinates>")
    $null = $sb.AppendLine('          </LinearRing>')
    $null = $sb.AppendLine('        </outerBoundaryIs>')
    if ($innerRingsXml.Length -gt 0) {
        $null = $sb.Append($innerRingsXml.ToString())
    }
    $null = $sb.AppendLine('      </Polygon>')
    $null = $sb.AppendLine('    </Placemark>')
}

$null = $sb.AppendLine('  </Document>')
$null = $sb.AppendLine('</kml>')

# ---------------------------------------------------------------------------
# 5. Write the KML file (UTF-8 without BOM)
# ---------------------------------------------------------------------------
$utf8NoBom = [System.Text.UTF8Encoding]::new($false)
[System.IO.File]::WriteAllText($OutputPath, $sb.ToString(), $utf8NoBom)

Write-Host "KML written to $OutputPath"
Write-Host "Features converted: $($geojson.features.Count)"
