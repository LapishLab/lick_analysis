function [y, Fs] = load_audio_segment(audio_file, start, stop)
    info = audioinfo(audio_file);
    Fs = info.SampleRate;
    
    start_ind = round(start * Fs) + 1;
    end_ind = round(stop * Fs);
    
    y = audioread(audio_file, [start_ind,end_ind]);
end