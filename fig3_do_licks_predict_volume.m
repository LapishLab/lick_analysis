clear
load("all_days.mat")
exp_table.num_licks = cellfun(@height, exp_table.licks);
%% Scatter licks vs. ethanol consumed
f = figure(theme="light"); clf; hold on;
f.Position = [100 100 400 400];

t = sub_table(exp_table, {'lickometer', 1},{'fluid', 'ethanol'},{'sex','M'});
scatter(t.num_licks, t.consumed, 'filled')

t = sub_table(exp_table, {'lickometer', 1},{'fluid', 'ethanol'},{'sex','F'});
scatter(t.num_licks, t.consumed, 'filled')

xlabel('Total licks')
ylabel('Volume consumed (ml)')
title('Ethanol bottle')
legend("Male", "Female", Location="northwest")
exportgraphics(gca,['figures', filesep, 'f3_ethanol_licks.svg'])

%% Scatter licks vs. ethanol consumed
f = figure(theme="light"); clf; hold on;
f.Position = [100 100 400 400];

t = sub_table(exp_table, {'lickometer', 1},{'fluid', 'water'},{'sex','M'});
scatter(t.num_licks, t.consumed, 'filled')

t = sub_table(exp_table, {'lickometer', 1},{'fluid', 'water'},{'sex','F'});
scatter(t.num_licks, t.consumed, 'filled')

xlabel('Total licks')
ylabel('Volume consumed (ml)')
title('Water bottle')
legend("Male", "Female", Location="northwest")
exportgraphics(gca,['figures', filesep, 'f3_water_licks.svg'])