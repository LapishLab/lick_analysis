clear
%% settings
time_stop = 1000 * 60 * 60; % 1 hour max
average_lick_duration = 100 ; % milliseconds
licks_per_ml = 1000 / 6;
%% load experiment_structure.csv
exp_table = readtable('experiment_structure.csv');
timestamps = [];
sipper = [];

total_consumed = exp_table.consumed_L + exp_table.consumed_R;
r_prop = exp_table.consumed_R ./ total_consumed;
total_licks = total_consumed * licks_per_ml;
total_licks = round(total_licks + total_licks .* (rand(size(total_licks))-.5)/10);
for r = 1:height(exp_table)
    if exp_table.lickometer(r) == 0
        continue
    end
    t =  generate_lick_times(total_licks(r), time_stop);
    is_right = model_bottle_switching(length(t), r_prop(r));
    s = nan(size(is_right));
    s(is_right) = exp_table.sipper_R(r);
    s(~is_right) = exp_table.sipper_L(r);

    timestamps =  [timestamps; t];
    sipper = [sipper;s];
end

%%




lick_table = table();
lick_table.timestamp = timestamps;
lick_table.sipper_id = sipper;
lick_table.state(:) = 1;

duration = average_lick_duration + randn(height(lick_table),1)*20; 
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
writetable(lick_table, 'licks_20250000_000000.csv');

function lick_times = generate_lick_times(num_licks, time_stop)
    chi_shape = randi(10);
    lick_times = random('Chisquare',chi_shape,[num_licks,1]);
    lick_times = sort(lick_times);
    lick_times = lick_times(1:end-1) / lick_times(end) * time_stop;
    lick_times(diff(lick_times)<40) = [];
end

function is_right = model_bottle_switching(num_licks, right_prop)
clumpy_factor = 20;
smooth_rand = smooth(randn([num_licks,1]), clumpy_factor);
sorted = sort(smooth_rand);
threshold = sorted(round(num_licks*right_prop));
is_right = smooth_rand<threshold;
end