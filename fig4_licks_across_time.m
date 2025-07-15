clear
load("all_days.mat")
exp_table = exp_table(exp_table.lickometer==1, :);
size = [400, 300];
%% bin licks
% max_t = 3*60*60*1000; % full 3 hours
max_t = 30*60*1000; % first 30 minutes
bin_size = 1000 * 100;

edges = 0:bin_size:max_t;
x_time = (edges(2:end) - diff(edges(1:2))/2)/ 1000 / 60; % time in seconds
lick_rate = bin_licks(exp_table.licks, edges);
%% Lick rate across time ethanol vs. water
f = figure(1); theme('light'); clf; hold on;
f.Position = [80 80 size];
eth = lick_rate(strcmp(exp_table.fluid, 'ethanol'), :);
wat = lick_rate(strcmp(exp_table.fluid, 'water'), :);
shadedErrorBar(x_time,eth,{@mean,@sem}, 'lineProps', 'b');
shadedErrorBar(x_time,wat,{@mean,@sem}, 'lineProps', 'r');
xlabel('Time (min)')
ylabel('Lick rate (Hz)')
legend("ethanol", "water")

exportgraphics(gca,['figures', filesep, 'f4_ethanol_vs_water.svg'])
%% Ethanol Lick rate across time P vs. Wistar
f = figure(2); theme('light'); clf; hold on;
f.Position = [120 120 size];
is_eth = strcmp(exp_table.fluid, 'ethanol');
is_P = exp_table.strain=="P";
is_Wis = exp_table.strain=="W";

shadedErrorBar(x_time,lick_rate(is_Wis & is_eth,:),{@mean,@sem}, 'lineProps', 'b');
shadedErrorBar(x_time,lick_rate(is_P & is_eth,:),{@mean,@sem}, 'lineProps', 'r');
xlabel('Time (min)')
ylabel('Lick rate (Hz)')
legend("Wistar", "P")

exportgraphics(gca,['figures', filesep, 'f4_P_vs_Wistart_for_ethanol.svg'])
%% Ethanol Lick rate across time Male vs Female
f = figure(3); theme('light'); clf; hold on;
f.Position = [160 160 size];
is_male = exp_table.sex=="M";
is_female = exp_table.sex=="F";
shadedErrorBar(x_time,lick_rate(is_female & is_eth,:),{@mean,@sem}, 'lineProps', 'b');
shadedErrorBar(x_time,lick_rate(is_male & is_eth,:),{@mean,@sem}, 'lineProps', 'r');
xlabel('Time (min)')
ylabel('Lick rate (Hz)')
legend("Female", "Male")

exportgraphics(gca,['figures', filesep, 'f4_M_vs_F_for_ethanol.svg'])

%% Ethanol Lick rate for each day
f = figure(4); theme('light'); clf; hold on;
f.Position = [200 200 size];

is_day = exp_table.day == "day1";
shadedErrorBar(x_time,lick_rate(is_eth & is_day,:),{@mean,@sem}, 'lineProps', 'b');
is_day = exp_table.day == "day2";
shadedErrorBar(x_time,lick_rate(is_eth & is_day,:),{@mean,@sem}, 'lineProps', 'r');
is_day = exp_table.day == "day3";
shadedErrorBar(x_time,lick_rate(is_eth & is_day,:),{@mean,@sem}, 'lineProps', 'g');
is_day = exp_table.day == "day4";
shadedErrorBar(x_time,lick_rate(is_eth & is_day,:),{@mean,@sem}, 'lineProps', 'k');

xlabel('Time (min)')
ylabel('Lick rate (Hz)')
legend("day 1", "day 2", "day 3", "day 4")

exportgraphics(gca,['figures', filesep, 'f4_by_day_for_ethanol.svg'])


%%

function lick_rate = bin_licks(licks, edges)
lick_rate = nan(length(licks), length(edges)-1);
for i=1:length(licks)
    l = licks{i};
    start_times = l{:,1};
    lick_rate(i, :) = histcounts(start_times, edges);
end
lick_rate = lick_rate / diff(edges(1:2));
end