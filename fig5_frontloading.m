clear
load("all_days.mat")
exp_table = sub_table(exp_table, {'lickometer', 1});

water_color = [35, 37, 150] / 255;
eth_color = [4, 64, 15] / 255;
%% restrict by lick volume
thresh = [2, 25];
num_licks = cellfun(@height, exp_table.licks);
lick_vol = exp_table.consumed ./ num_licks *1000;
is_good = lick_vol > thresh(1) & lick_vol < thresh(2);
exp_table = exp_table(is_good, :);


%% when do all licks occur
lick_times = cat(1, exp_table.licks{:}).start / 1000/ 60;

f = figure(1); theme('light'); clf; hold on;
size = [600, 500];
f.Position = [80 80 size];

[f,x] =ecdf(lick_times);
f(f>.5) = 1 - f(f>.5);
plot(x,f, 'k', 'LineWidth',3)
xlabel('Time (min)')
ylabel('Proportion of licks')
xlim([0,160])

[~, min_index] = min(abs(f-.5));
median_lick_time = x(min_index);
xline(median_lick_time, '--', 'LineWidth',3)
text(median_lick_time+3, .1, "Median = " +  num2str(round(median_lick_time,1)) + " min", 'FontSize', 20)


set(gca,'fontsize', 20) 
exportgraphics(gca,['figures', filesep, 'f5_all_lick_times.svg'])

%% frontloading ethanol  
t = median_lick_time * 60 * 1000; % Time cutoff to count proportion of "early" licks

labels =  ["Male Wistar","Female Wistar","Male P","Female P"];
data = cell(length(labels),2);

s = sub_table(exp_table, {'sex','M'}, {'strain', 'W'}, {'fluid', "water"});
data{1,1} = licks_by_time(s.licks, t);
s = sub_table(exp_table, {'sex','M'}, {'strain', 'W'}, {'fluid', "ethanol"});
data{1,2} = licks_by_time(s.licks, t);

s = sub_table(exp_table, {'sex','F'}, {'strain', 'W'}, {'fluid', "water"});
data{2,1} = licks_by_time(s.licks, t);
s = sub_table(exp_table, {'sex','F'}, {'strain', 'W'}, {'fluid', "ethanol"});
data{2,2} = licks_by_time(s.licks, t);

s = sub_table(exp_table, {'sex','M'}, {'strain', 'P'}, {'fluid', "water"});
data{3,1} = licks_by_time(s.licks, t);
s = sub_table(exp_table, {'sex','M'}, {'strain', 'P'}, {'fluid', "ethanol"});
data{3,2} = licks_by_time(s.licks, t);

s = sub_table(exp_table, {'sex','F'}, {'strain', 'P'}, {'fluid', "water"});
data{4,1} = licks_by_time(s.licks, t);
s = sub_table(exp_table, {'sex','F'}, {'strain', 'P'}, {'fluid', "ethanol"});
data{4,2} = licks_by_time(s.licks, t);


%%
f = figure(2); theme('light'); clf; hold on;
size = [900, 500];
f.Position = [80 80 size];
b = errbar_with_raw_data(data, ["Male Wistar","Female Wistar","Male P","Female P"]);

b(1).FaceColor = water_color;
b(2).FaceColor = eth_color;

ylabel({"Licks occuring prior", "to overall median (%)"})
ylim([0,100])

legend('water', 'ethanol', Location='eastoutside')
set(gca,'fontsize', 20) 
exportgraphics(gca,['figures', filesep, 'f5_frontloading.svg'])

%% functions

function prop = licks_by_time(licks, time)
    prop = nan(size(licks));
    for i=1:length(licks)
        l = licks{i}.start;
        prop(i) = mean(l<time);
    end
    prop = rmmissing(prop);
    prop = prop*100;
end

% function errbar_with_raw_data(data, labels)
% % data = table or matrix with each column being different dataset
% % string labels for each group (x-axis of bar graph)
% avg = cellfun(@mean, data);
% err = cellfun(@sem, data);
% 
% bar(labels, avg)
% errorbar(avg,err, 'k', 'LineStyle', 'none', 'CapSize',50,'LineWidth',2)
% 
% 
% for i=1:length(data)
%     d = data{i};
%     x = repmat(i,length(d),1);
% 
%     jiggle_scale = .1;
%     x_jiggle = jiggle_scale*(randn(size(x)));
%     x = x + x_jiggle;
%     scatter(x,d, 'filled', 'k')
% end
% 
% 
% max_v = max(cellfun(@max, data));
% ylim([0, max_v*1.1])
% 
% end

function b = errbar_with_raw_data(data, labels)
% data = table or matrix with each column being different dataset
% string labels for each group (x-axis of bar graph)

avg = cellfun(@mean,data);
err = cellfun(@sem,data);

b = bar(labels, avg, 'FaceColor','flat');

x = cell2mat({b.XEndPoints}');
avg = avg';
err = err';

errorbar(x(:), avg(:), err(:), 'k', 'LineStyle', 'none', 'CapSize',20,'LineWidth',2)

jiggle_scale = .02;
for r = 1:size(x,1)
    for c = 1:size(x,2)
        d = data{c,r};
        bar_x = repmat(x(r,c), length(d), 1);
        bar_x = bar_x + jiggle_scale*(randn(size(bar_x)));

        scatter(bar_x,d, 'filled', 'k')
    end
end

% ylim([0, max(data(:))*1.1])
end