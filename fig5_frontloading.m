clear
load("all_days.mat")
size = [800, 300];
exp_table = sub_table(exp_table, {'lickometer', 1});
%% when do all licks occur
% lick_times = cat(1, exp_table.licks{:}).start;
% figure(1); clf
% ecdf(lick_times)

%% split by M/F, P/W, 
t = 15 * 60 * 1000; % Time cutoff to count proportion of "early" licks
data = cell(4,1);
fluid = 'ethanol';
s = sub_table(exp_table, {'sex','M'}, {'strain', 'W'}, {'fluid', fluid});
data{1} = licks_by_time(s.licks, t);

s = sub_table(exp_table, {'sex','F'}, {'strain', 'W'}, {'fluid', fluid});
data{2} = licks_by_time(s.licks, t);

s = sub_table(exp_table, {'sex','M'}, {'strain', 'P'}, {'fluid', fluid});
data{3} = licks_by_time(s.licks, t);

s = sub_table(exp_table, {'sex','F'}, {'strain', 'P'}, {'fluid', fluid});
data{4} = licks_by_time(s.licks, t);

f = figure(1); theme('light'); clf; hold on;
f.Position = [80 80 size];
errbar_with_raw_data(data, ["Male Wistar","Female Wistar","Male P","Female P"])
ylabel({"Licks occuring within", "first 15 minutes (%)"})
ylim([0,100])
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

function errbar_with_raw_data(data, labels)
% data = table or matrix with each column being different dataset
% string labels for each group (x-axis of bar graph)
avg = cellfun(@mean, data);
err = cellfun(@sem, data);

bar(labels, avg)
errorbar(avg,err, 'k', 'LineStyle', 'none', 'CapSize',50,'LineWidth',2)


for i=1:length(data)
    d = data{i};
    x = repmat(i,length(d),1);

    jiggle_scale = .1;
    x_jiggle = jiggle_scale*(randn(size(x)));
    x = x + x_jiggle;
    scatter(x,d, 'filled', 'k')
end


max_v = max(cellfun(@max, data));
ylim([0, max_v*1.1])

end