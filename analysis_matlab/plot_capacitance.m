%% capacitance recording expected to be text file in current directory
cap_file_name = dir('*.txt').name;

%% load capacitance values
cap_values = readmatrix(cap_file_name);

%% plot capacitance
figure(1); clf; hold on;
plot(cap_values(:,1), cap_values(:,2))
plot(cap_values(:,1), cap_values(:,3))

legend("R","L")
xlabel("Time (s)")
ylabel("Capacitance (arb)")

%% choose a time of interest for later video / audio viewing
c_time = 946; % time in seconds into the capacitance recording

pre_time = 1;
post_time = 5;

cap_toi = date_from_filename(cap_file_name) + seconds(c_time);