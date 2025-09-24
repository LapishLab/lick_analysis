function play_audio(audio_file, start, stop)
    [y, Fs] = load_audio_segment(audio_file, start, stop);

    max_Fs = 196000;
    if Fs > max_Fs
        decimation_factor = ceil(Fs / max_Fs);
        Fs = round(Fs/decimation_factor);
        y = decimate(y, decimation_factor);
    end
    
    sound(y, Fs);
end