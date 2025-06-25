clear
folders = dir();
folders = folders(3:end, :);

exp_table = table();

for ind = 1:height(folders)
    csv_name = string(folders(ind).name) + filesep + 'experiment_structure.csv';
    day_table = readtable(csv_name);
    day_table.day(:) = ind;
    exp_table = cat(1, exp_table, day_table);

end

%% get lick vs no lick data
exp_table = sortrows(exp_table,"day","ascend");
exp_table = sortrows(exp_table,"rat_id","ascend");

has_lickometer = exp_table.lickometer == 1;
no_lickometer = exp_table.lickometer == 0;    

data_with_lickometer = exp_table.consumed_R(has_lickometer);
data_without_lickometer = exp_table.consumed_R(no_lickometer);

if any(~(exp_table.rat_id(has_lickometer) == exp_table.rat_id(no_lickometer)))
    warning("This design isn't properly counterbalanced or sorted for paired t-test")
end

%% calculate the mean and standard error of ethanol consumed for each group
mean_with_lickometer = mean(data_with_lickometer);
mean_without_lickometer = mean(data_without_lickometer);
se_with_lickometer = std(data_with_lickometer) / sqrt(length(data_with_lickometer));
se_without_lickometer = std(data_without_lickometer) / sqrt(length(data_without_lickometer));
y = [mean_with_lickometer, mean_without_lickometer];
error = [se_with_lickometer, se_without_lickometer];
%% create error bar graph with standard error lines
figure(1); clf; hold on;
bar(["lickometer", "no lickometer"], y)
errorbar(y,error, 'LineStyle', 'none')
scatter(1, data_with_lickometer, 'filled', 'b')
scatter(2, data_without_lickometer, 'filled', 'r')

[~, p] = ttest(data_with_lickometer,data_without_lickometer)
