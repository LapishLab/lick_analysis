clear
fig_size = [400,400];
load("all_days.mat")
exp_table.num_licks = cellfun(@height, exp_table.licks);
exp_table.lick_vol = exp_table.consumed ./ exp_table.num_licks *1000;
exp_table = sub_table(exp_table, {'lickometer', 1});

lightening = 1.5;
water_color = [35, 37, 150] / 255 * lightening;
eth_color = [4, 64, 15] / 255 * lightening;
%% Scatter licks vs. ethanol consumed
f = figure(1); theme('light'); clf; hold on;
f.Position = [80 80 fig_size];
sz = 25;

w = sub_table(exp_table, {'fluid', 'water'});
scatter(w.num_licks, w.consumed, sz, water_color, 'filled')

e = sub_table(exp_table, {'fluid', 'ethanol'});
scatter(e.num_licks, e.consumed, sz, eth_color, 'filled')

xlabel('Total licks')
ylabel('Volume consumed (ml)')
legend("Water", "10% ethanol", Location="best")
exportgraphics(gca,['figures', filesep, 'f3_ethanol_licks.svg'])

%% Scatter licks vs. ethanol consumed
f = figure(2); theme('light'); clf; hold on;
f.Position = [480 80 fig_size];

edges = 0:1:35; % volume in uL
edges = [edges, inf];
histogram(exp_table.lick_vol, edges)

xlabel('Lick volume (uL)')
ylabel('count')

xline(2, '--')
xline(25, '--')

exportgraphics(gca,['figures', filesep, 'f3_ethanol_volumes.svg'])

