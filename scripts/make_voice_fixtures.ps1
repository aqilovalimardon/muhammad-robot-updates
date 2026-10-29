$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Speech
New-Item -ItemType Directory -Force voice-fixtures | Out-Null
$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
$format = New-Object System.Speech.AudioFormat.SpeechAudioFormatInfo(16000, [System.Speech.AudioFormat.AudioBitsPerSample]::Sixteen, [System.Speech.AudioFormat.AudioChannel]::Mono)
try {
    foreach ($command in @('hello', 'close', 'open')) {
        $path = Join-Path $PWD "voice-fixtures/$command.wav"
        $synth.SetOutputToWaveFile($path, $format)
        $synth.Speak("$command robot")
        $synth.SetOutputToNull()
    }
} finally { $synth.Dispose() }
Write-Output 'PASS: actual offline Windows speech fixtures generated'
