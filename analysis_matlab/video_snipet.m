
%% get video file name and start/stop times
video_file = wildcard_path('test01\cam\*.mp4');
video_time = file_time_for_toi(video_file, cap_toi);
start = seconds(video_time) - pre_time;
stop = seconds(video_time) + post_time;

%% play video
figure(2); clf;
play_video(video_file, start, stop);
