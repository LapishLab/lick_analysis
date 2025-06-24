clear
%%
max_sippers = 18*2;
time_start = 0;
time_stop = 1000 * 60 * 60; % 1 hour max
num_data_points = 18 * 2 * time_stop / 1000; % around 2 licks/s per cage
average_lick_duration = 100 ; % milliseconds
%%

lick_table = table();
lick_table.timestamp = randi(time_stop, num_data_points, 1);
lick_table.sipper_id = randi(max_sippers, num_data_points, 1) - 1;
lick_table.state(:) = 1;

duration = average_lick_duration + randn(num_data_points,1)*20; 
duration(duration<40) = duration(duration<40)+40;
duration = round(duration);

lick_table_off = table();
lick_table_off.timestamp = lick_table.timestamp + duration;
lick_table_off.sipper_id = lick_table.sipper_id;
lick_table_off.state(:) = 0;

%%
lick_table = [lick_table; lick_table_off];
lick_table = sortrows(lick_table,"timestamp","ascend");

%%
writetable(lick_table, 'randomly_generated.csv');