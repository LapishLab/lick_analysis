clear

lick_table = readtable(dir("licks_*.csv").name);
exp_table = readtable('experiment_structure.csv');
%% Plot average cumulative consumption of ethanol for Wistar vs. P

% Get sipper IDs for Wistar ethanol
is_wistar = exp_table.strain == "Wistar";
is_ethanol_trial = exp_table.fluid_R == "ethanol";
wistar_ethanol_sippers = exp_table.sipper_R(is_wistar & is_ethanol_trial);

% Get sipper IDs for Ps ethanol
is_P = exp_table.strain == "P";
is_ethanol_trial = exp_table.fluid_R == "ethanol";
P_ethanol_sippers = exp_table.sipper_R(is_P & is_ethanol_trial);

% Plot wistar_ethanol_sippers
figure(1); clf; hold on;

plot_sipper(lick_table, wistar_ethanol_sippers);
plot_sipper(lick_table, P_ethanol_sippers);


xlabel("time (milliseconds)")
ylabel("cumulative lick number")
legend("wistar", "P")

%% Plot all sippers
figure(1); clf; hold on;
for index = 0:max(lick_table.sipper_id)
    plot_sipper(lick_table, index)
end

xlabel("time (milliseconds)")
ylabel("cumulative lick number")
legend

%% Functions
function [x,y] = plot_sipper(random_table, sipper_id)
is_lick_start = random_table.state == 1;
is_sipper = random_table.sipper_id == sipper_id';
is_sipper = any(is_sipper, 2);
is_what_I_want = is_lick_start & is_sipper;
lickTimes = random_table.timestamp(is_what_I_want);

[f,x] = ecdf(lickTimes);
y = f * length(lickTimes);
plot(x,y)
end