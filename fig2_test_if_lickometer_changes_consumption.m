clear
load("all_days.mat")

consumption = cell(2,1); % 1 = water (no lick, lick), 2 = ethanol (no lick, lick)

%% get water consumption
wat = sub_table(exp_table, {'fluid', 'water'});
w_consumption = consumption_split_by_lickometer(wat);
consumption{1} = w_consumption; 

%% get ethanol consumption
eth = sub_table(exp_table, {'fluid', 'ethanol'});
e_consumption = consumption_split_by_lickometer(eth);
consumption{2} = e_consumption;
%% Plot bar graph of ethanol volume consumed
f = figure(1); theme('light'); clf; hold on;
fig_size = [500,400];
f.Position = [80 80 fig_size];

b = errbar_with_raw_data(consumption, ["Water", "10% ethanol"]);

water_color = [35, 37, 150] / 255;
eth_color = [4, 64, 15] / 255;
lightening = 2.5;
b(1).CData(1,:) =  water_color * lightening; %no_lick_water
b(1).CData(2,:)  = eth_color * lightening; % no_lick_eth
b(2).CData(1,:) = water_color; %  lick_water
b(2).CData(2,:) = eth_color; %lick_eth 

ylabel('Volume consumed (ml)')


exportgraphics(gca,['figures', filesep, 'f2_ethanol_consumption.svg'])

% [~, p] = ttest(e_consumption(:,1), e_consumption(:,2));



%% Plot bar graph of consumption percentage with lickometer
f = figure(2); theme('light'); clf; hold on;
fig_size = [300,400];
f.Position = [480 80 fig_size];
difference = table();
difference.water = (w_consumption.lick - w_consumption.no_lick);
difference.ethanol = (e_consumption.lick - e_consumption.no_lick);
b = errbar_with_raw_data2({difference}, ["Water", "10% Ethanol"]);

b(1).CData(1,:) =  water_color * lightening/2; %no_lick_water
b(1).CData(2,:)  = eth_color * lightening/2; % no_lick_eth

ylabel('Consumption difference with lick detector (ml)')

ylim(ylim*1.1)
exportgraphics(gca,['figures', filesep, 'f2_diff_consumption.svg'])


%%

function b = errbar_with_raw_data(data, labels)
% data = table or matrix with each column being different dataset
% string labels for each group (x-axis of bar graph)

avg = nan(length(data), width(data{1}));
err = avg;

for i=1:length(data)
    d = table2array(data{i});
    avg(i,:) = mean(d);
    err(i,:) = sem(d);
end
b = bar(labels, avg, 'FaceColor','flat');

x = cell2mat({b.XEndPoints}');
avg = avg';
err = err';

errorbar(x(:), avg(:), err(:), 'k', 'LineStyle', 'none', 'CapSize',20,'LineWidth',2)

jiggle_scale = .02;
for r = 1:size(x,1)
    for c = 1:size(x,2)
        d = data{c}{:,r};
        bar_x = repmat(x(r,c), length(d), 1);
        bar_x = bar_x + jiggle_scale*(randn(size(bar_x)));

        scatter(bar_x,d, 'filled', 'k')
    end
end

% ylim([0, max(data(:))*1.1])
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

function b = errbar_with_raw_data2(data, labels)
% data = table or matrix with each column being different dataset
% string labels for each group (x-axis of bar graph)

avg = nan(length(data), width(data{1}));
err = avg;

for i=1:length(data)
    d = table2array(data{i});
    avg(i,:) = mean(d);
    err(i,:) = sem(d);
end
b = bar(labels, avg, 'FaceColor','flat');

x = cell2mat({b.XEndPoints}');
avg = avg';
err = err';

errorbar(x(:), avg(:), err(:), 'k', 'LineStyle', 'none', 'CapSize',20,'LineWidth',2)

jiggle_scale = .1;

for c = 1:size(x,2)
    d = data{1}{:,c};
    bar_x = repmat(x(c), length(d), 1);
    bar_x = bar_x + jiggle_scale*(randn(size(bar_x)));

    scatter(bar_x,d, 'filled', 'k')
end
end