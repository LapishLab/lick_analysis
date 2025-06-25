clear
%% settings
time_stop = 1000 * 60 * 60; % 1 hour max

lick_rate = 1; % Hz

ethanol_prop_baseline = 0.8; % proportion of time drinking ethanol
wistar_reduction = 0.7; % wistar drink less
male_reduction = 0.8; % males drink less

average_lick_duration = 100 ; % milliseconds
%% load experiment_structure.csv
exp_table = readtable('experiment_structure.csv');
timestamps = [];
sipper = [];

for r = 1:height(exp_table)
    if exp_table.lickometer(r) == 0
        continue
    end
    noisy_rate = lick_rate + (randi(200)-100)/100/10/lick_rate; %add up to 10% noise
    t =  generate_lick_times(noisy_rate, time_stop);

    if exp_table.fluid_R{r} == "water"
        right_prop = 0.5;
    else
        right_prop = ethanol_prop_baseline;
        if exp_table.strain{r} == "Wistar"
            right_prop = right_prop * wistar_reduction;
        end
        if exp_table.sex{r} == "F"
            right_prop = right_prop * male_reduction;
        end
    end
    is_right = model_bottle_switching(length(t), right_prop);
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
writetable(lick_table, 'randomly_generated.csv');

function lick_times = generate_lick_times(lick_rate, time_stop)
    num_licks = round(lick_rate * time_stop / 1000);
    chi_shape = randi(10);
    lick_times = random('Chisquare',chi_shape,[num_licks,1]);
    lick_times = sort(lick_times);
    lick_times = lick_times(1:end-1) / lick_times(end) * time_stop;
    lick_times(diff(lick_times)<40) = [];
end

function is_right = model_bottle_switching(num_licks, right_prop)
is_right = zeros(num_licks);
is_right(1: round(num_licks*right_prop)) = 1;
is_right = is_right(randperm(num_licks));
lick_smoothing = 20;
is_right = round(smooth(is_right, lick_smoothing));
is_right = logical(is_right);
end