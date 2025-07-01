load("all_days.mat")

%% get lick vs no lick data
exp_table = sortrows(exp_table,"day","ascend");
exp_table = sortrows(exp_table,"rat_id","ascend");

has_lickometer = exp_table.lickometer == 1;  
if any(~(exp_table.rat_id(has_lickometer) == exp_table.rat_id(~has_lickometer)))
    warning("This design isn't properly counterbalanced or sorted for paired t-test")
end


%% Plot bar graph of ethanol volume consumed
f = figure(theme="light"); clf; hold on;
f.Position = [100 100 400 400];

no_lickometer = exp_table.consumed_R(~has_lickometer);
with_lickometer = exp_table.consumed_R(has_lickometer);

errbar_with_raw_data({no_lickometer, with_lickometer}, ...
    ["No lickometer", "With lickometer"])
ylabel('Volume consumed (ml)')
title('Ethanol bottle')
exportgraphics(gca,['figures', filesep, 'f2_ethanol_consumption.svg'])

[~, p] = ttest(no_lickometer, with_lickometer)

%% Plot bar graph of water volume consumed
f = figure(theme="light"); clf; hold on;
f.Position = [100 100 400 400];

no_lickometer = exp_table.consumed_L(~has_lickometer);
with_lickometer = exp_table.consumed_L(has_lickometer);

errbar_with_raw_data({no_lickometer, with_lickometer}, ...
    ["No lickometer", "With lickometer"])
ylabel('Volume consumed (ml)')
title('water bottle')
exportgraphics(gca,['figures', filesep, 'f2_water_consumption.svg'])

[~, p] = ttest(no_lickometer, with_lickometer)



function errbar_with_raw_data(data, labels)
% data = cell array of raw data in each group
% string labels for each group (x-axis of bar graph)

avg = cellfun(@mean, data);
err = cellfun(@sem, data);

bar(labels, avg)
errorbar(avg,err, 'k', 'LineStyle', 'none', 'CapSize',50,'LineWidth',2)

jiggle_scale = .4;
for i=1:length(data)
    y = data{i};
    x = i + jiggle_scale*(rand(size(y))-0.5);
    scatter(x,y, 'filled', 'k')
end
end