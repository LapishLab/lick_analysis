function plot_spectrum(audio_file, start, stop)
    [y, Fs] = load_audio_segment(audio_file, start, stop);
    
    window = round(Fs * 0.01); % 100 ms window
    % spectrogram(y,window,[],[], Fs, "yaxis")
    [~,F,T,P] = spectrogram(y,window,[],[], Fs);
  
    imagesc(T, F/1000, 10*log10(P+eps)); % Add eps to avoid log(0)
    axis xy;
    ylabel('Frequency (kHz)');
    xlabel('Time (s)');
    c = colorbar;
    c.Label.String = 'PSD (dB/Hz)';
end