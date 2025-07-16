clear
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
f.Position = [480 80 fig_size];

errbar_with_raw_data(w_consumption, ["No lick detector", "With lick detector"])
ylabel('Volume consumed (ml)')
title('Water')
exportgraphics(gca,['figures', filesep, 'f2_water_consumption.svg'])

% [~, p] = ttest(w_consumption(:,1), w_consumption(:,2))

%% Plot bar graph of consumption percentage with lickometer
f = figure(3); theme('light'); clf; hold on;
f.Position = [880 80 fig_size];
difference = table();
difference.water = (w_consumption.lick - w_consumption.no_lick);
difference.ethanol = (e_consumption.lick - e_consumption.no_lick);
errbar_with_raw_data(difference, ["Water", "10% Ethanol"])
ylabel('Consumption difference with lick detector (ml)')
title('Consumption change per rat')
ylim([min(difference{:,:}, [], 'all'), max(difference{:,:}, [], 'all')])
exportgraphics(gca,['figures', filesep, 'f2_diff_consumption.svg'])


%%

function errbar_with_raw_data(data, labels)
% data = table or matrix with each column being different dataset
% string labels for each group (x-axis of bar graph)
data = table2array(data);
avg = mean(data);
err = sem(data);

bar(labels, avg)
errorbar(avg,err, 'k', 'LineStyle', 'none', 'CapSize',50,'LineWidth',2)

x = 1:size(data,2);
x = repmat(x,size(data,1),1);

jiggle_scale = .1;
x_jiggle = jiggle_scale*(randn(size(x)));
x = x + x_jiggle;
scatter(x,data, 'filled', 'k')
ylim([0, max(data(:))*1.1])

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

    consumption = rmmissing(consumption);
end

