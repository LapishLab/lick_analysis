clear
fig_size = [400,400];
load("all_days.mat")
exp_table.num_licks = cellfun(@height, exp_table.licks);
%% Scatter licks vs. ethanol consumed
f = figure(1); theme('light'); clf; hold on;
f.Position = [80 80 fig_size];

t = sub_table(exp_table, {'lickometer', 1},{'fluid', 'ethanol'},{'sex','M'});
scatter(t.num_licks, t.consumed, 'filled')

t = sub_table(exp_table, {'lickometer', 1},{'fluid', 'ethanol'},{'sex','F'});
scatter(t.num_licks, t.consumed, 'filled')

xlabel('Total licks')
ylabel('Volume consumed (ml)')
title('10% Ethanol')
legend("Male", "Female", Location="northwest")
exportgraphics(gca,['figures', filesep, 'f3_ethanol_licks.svg'])

%% Scatter licks vs. ethanol consumed
f = figure(2); theme('light'); clf; hold on;
f.Position = [480 80 fig_size];

t = sub_table(exp_table, {'lickometer', 1},{'fluid', 'water'},{'sex','M'});
scatter(t.num_licks, t.consumed, 'filled')

t = sub_table(exp_table, {'lickometer', 1},{'fluid', 'water'},{'sex','F'});
scatter(t.num_licks, t.consumed, 'filled')

xlabel('Total licks')
ylabel('Volume consumed (ml)')
title('Water')
legend("Male", "Female", Location="northwest")
exportgraphics(gca,['figures', filesep, 'f3_water_licks.svg'])