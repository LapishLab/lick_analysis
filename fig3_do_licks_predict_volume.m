clear
load("all_days.mat")
exp_table = exp_table(exp_table.lickometer==1, :);
is_male = exp_table.sex=="M";
exp_table.num_licks_R = cellfun(@height, exp_table.licks_R);
exp_table.num_licks_L = cellfun(@height, exp_table.licks_L);
%% Scatter licks vs. ethanol consumed
f = figure(theme="light"); clf; hold on;
f.Position = [100 100 400 400];

x = exp_table.num_licks_R(is_male);
y = exp_table.consumed_R(is_male);
scatter(x, y , 'filled')

x = exp_table.num_licks_R(~is_male);
y = exp_table.consumed_R(~is_male);
scatter(x, y , 'filled')

xlabel('Total licks')
ylabel('Volume consumed (ml)')
title('Ethanol bottle')
legend("Male", "Female", Location="northwest")
exportgraphics(gca,['figures', filesep, 'f3_ethanol_licks.svg'])

%% Scatter licks vs. ethanol consumed
f = figure(theme="light"); clf; hold on;
f.Position = [100 100 400 400];

x = exp_table.num_licks_L(is_male);
y = exp_table.consumed_L(is_male);
scatter(x, y , 'filled')

x = exp_table.num_licks_L(~is_male);
y = exp_table.consumed_L(~is_male);
scatter(x, y , 'filled')

xlabel('Total licks')
ylabel('Volume consumed (ml)')
title('Water bottle')
legend("Male", "Female", Location="northwest")
exportgraphics(gca,['figures', filesep, 'f3_water_licks.svg'])