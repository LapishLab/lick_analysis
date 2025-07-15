load("all_days.mat")
fig_size = [400,400];
%% get ethanol consumption
eth = sub_table(exp_table, {'fluid', 'ethanol'});
e_consumption = consumption_split_by_lickometer(eth);

%% Plot bar graph of ethanol volume consumed
f = figure(1); theme('light'); clf; hold on;
f.Position = [80 80 fig_size];

errbar_with_raw_data(e_consumption, ["No lick detector", "With lick detector"])
ylabel('Volume consumed (ml)')
title('10% Ethanol')
exportgraphics(gca,['figures', filesep, 'f2_ethanol_consumption.svg'])

% [~, p] = ttest(e_consumption(:,1), e_consumption(:,2));

%% get water consumption
wat = sub_table(exp_table, {'fluid', 'water'});
w_consumption = consumption_split_by_lickometer(wat);

%% Plot bar graph of water volume consumed
f = figure(2); theme('light'); clf; hold on;
f.Position = [80 80 fig_size];

errbar_with_raw_data(w_consumption, ["No lick detector", "With lick detector"])
ylabel('Volume consumed (ml)')
title('Water')
exportgraphics(gca,['figures', filesep, 'f2_water_consumption.svg'])

% [~, p] = ttest(w_consumption(:,1), w_consumption(:,2))

function errbar_with_raw_data(data, labels)
% data = table or matrix with each column being different dataset
% string labels for each group (x-axis of bar graph)
data = table2array(data);
data(isnan(data)) = 0;
avg = mean(data);
err = std(data);

bar(labels, avg)
errorbar(avg,err, 'k', 'LineStyle', 'none', 'CapSize',50,'LineWidth',2)

x = 1:size(data,2);
x = repmat(x,size(data,1),1);

jiggle_scale = .1;
x_jiggle = jiggle_scale*(randn(size(x)));
x = x + x_jiggle;
scatter(x,data, 'filled', 'k')
end

function vol = consumption_per_rat(rat_ids, exp)
    vol = nan(size(rat_ids));
    for i=1:length(rat_ids)
        c = exp.consumed(rat_ids(i)==exp.rat_id);
        vol(i) = mean(c);
    end

end

function consumption = consumption_split_by_lickometer(exp)
    rat_ids = unique(exp.rat_id);
    rat_ids(isnan(rat_ids)) = [];

    has_lickometer = exp.lickometer == 1;

    l = consumption_per_rat(rat_ids, exp(has_lickometer,:));
    n = consumption_per_rat(rat_ids, exp(~has_lickometer,:));

    consumption = table();
    consumption.lick = l;
    consumption.no_lick = n;
end

