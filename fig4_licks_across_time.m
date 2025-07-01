clear
load("all_days.mat")
exp_table = exp_table(exp_table.lickometer==1, :);
is_male = exp_table.sex=="M";
is_P = exp_table.strain=="P";
size = [600, 300];
%% bin licks
max_t = 60*60*1000;
bin_size = 1000 * 100;

edges = 0:bin_size:max_t;
x_time = (edges(2:end) - diff(edges(1:2))/2)/ 1000; % time in seconds
lick_rate_ethanol = bin_licks(exp_table.licks_R, edges);
lick_rate_water = bin_licks(exp_table.licks_L, edges);
%% Lick rate across time ethanol vs. water
f = figure(theme="light"); clf; hold on;
f.Position = [100 100 size];
shadedErrorBar(x_time,lick_rate_ethanol,{@mean,@sem}, 'lineProps', 'b');
shadedErrorBar(x_time,lick_rate_water,{@mean,@sem}, 'lineProps', 'r');
xlabel('Time (s)')
ylabel('Lick rate (Hz)')
legend("ethanol", "water")

exportgraphics(gca,['figures', filesep, 'f4_ethanol_vs_water.svg'])
%% Ethanol Lick rate across time P vs. Wistar
f = figure(theme="light"); clf; hold on;
f.Position = [100 100 size];
shadedErrorBar(x_time,lick_rate_ethanol(~is_P,:),{@mean,@sem}, 'lineProps', 'b');
shadedErrorBar(x_time,lick_rate_ethanol(is_P,:),{@mean,@sem}, 'lineProps', 'r');
xlabel('Time (s)')
ylabel('Lick rate (Hz)')
legend("Wistar", "P")

exportgraphics(gca,['figures', filesep, 'f4_P_vs_Wistart_for_ethanol.svg'])
%% Ethanol Lick rate across time Male vs Female
f = figure(theme="light"); clf; hold on;
f.Position = [100 100 size];
shadedErrorBar(x_time,lick_rate_ethanol(~is_male,:),{@mean,@sem}, 'lineProps', 'b');
shadedErrorBar(x_time,lick_rate_ethanol(is_male,:),{@mean,@sem}, 'lineProps', 'r');
xlabel('Time (s)')
ylabel('Lick rate (Hz)')
legend("Female", "Male")

exportgraphics(gca,['figures', filesep, 'f4_M_vs_F_for_ethanol.svg'])


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