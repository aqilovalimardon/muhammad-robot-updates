param([switch]$VariedInput)
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Speech
New-Item -ItemType Directory -Force voice-fixtures | Out-Null
$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
$format = New-Object System.Speech.AudioFormat.SpeechAudioFormatInfo(16000, [System.Speech.AudioFormat.AudioBitsPerSample]::Sixteen, [System.Speech.AudioFormat.AudioChannel]::Mono)
try {
    $phrases = [ordered]@{}
    foreach ($command in @('hello', 'close', 'open', 'fly', 'stop', 'jump')) {
        $phrases[$command] = "$command robot"
    }
    if ($VariedInput) {
        $phrases['flay'] = 'flay robot'
        $phrases['robot_fly'] = 'robot fly'
        $phrases['please_fly'] = 'please fly robot'
        $phrases['verb'] = 'fly'
        $phrases['wake'] = 'robot'
        $phrases['rope'] = 'jump rope'
        $phrases['music'] = 'stop the music'
        $phrases['negative'] = 'do not fly robot'
        $phrases['butterfly'] = 'a butterfly'
        $phrases['rump'] = 'rump robot'
        $phrases['cry'] = 'cry robot'
        $phrases['cry_alone'] = 'cry'
        $phrases['not_cry'] = 'do not cry robot'
    }
    foreach ($command in $phrases.Keys) {
        $path = Join-Path $PWD "voice-fixtures/$command.wav"
        $synth.SetOutputToWaveFile($path, $format)
        $synth.Speak($phrases[$command])
        $synth.SetOutputToNull()
    }
} finally { $synth.Dispose() }
Write-Output 'PASS: actual offline Windows speech fixtures generated'
