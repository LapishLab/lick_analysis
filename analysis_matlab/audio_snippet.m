%% audio file times
audio_files = wildcard_path('test01\mic\*.WAV');
[audio_time, audio_file] = file_time_for_toi(audio_files, cap_toi);

start = seconds(audio_time) - pre_time;
stop = seconds(audio_time) + post_time;
%% play audio at specific time

play_audio(audio_file, start, stop)


%% plot spectrum at specific time
figure(3); clf;
plot_spectrum(audio_file, start, stop)

ylim([0,100])
xline(pre_time, 'r--')