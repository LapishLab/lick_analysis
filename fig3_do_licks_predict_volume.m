clear
load("all_days.mat")
exp_table.num_licks = cellfun(@height, exp_table.licks);
exp_table.lick_vol = exp_table.consumed ./ exp_table.num_licks *1000;
exp_table = sub_table(exp_table, {'lickometer', 1});

lightening = 1.5;
water_color = [35, 37, 150] / 255 * lightening;
eth_color = [4, 64, 15] / 255 * lightening;
%% Scatter licks vs. ethanol consumed
f = figure(1); theme('light'); clf; hold on;
fig_size = [1000,600];
f.Position = [80 80 fig_size];
sz = 50;
set(gca,'fontsize', 20) 

w = sub_table(exp_table, {'fluid', 'water'});
scatter(w.num_licks, w.consumed, sz, water_color, 'filled')

e = sub_table(exp_table, {'fluid', 'ethanol'});
scatter(e.num_licks, e.consumed, sz, eth_color, 'filled')

% Fit all data
x = [w.num_licks ; e.num_licks];
y = [w.consumed; e.consumed];

ft = fittype('x*s', 'dependent',{'y'},'independent',{'x'},'coefficients',{'s'});
f = fit(x,y,ft, 'StartPoint', 0.005);

plot(xlim,f(xlim), '--')

% x = x(randperm(length(x)));

%% Normal R-squared calculation with y-intercept
% ss_res = sum( (y - f(x)).^2 );
% ss_tot = sum((y - mean(y)).^2);
% r_squared = 1 - (ss_res / ss_tot);

%% R squared calculation without y-intercept
r_squared = sum(f(x).^2) ./ sum(y.^2);
t_x = 2000;
text(t_x,f(t_x), "R^2="+num2str(round(r_squared,2)),'FontSize',20, 'VerticalAlignment','top','HorizontalAlignment','left')

xlabel('Total licks')
ylabel('Volume consumed (ml)')
legend("Water", "10% ethanol", Location="south")
exportgraphics(gca,['figures', filesep, 'f3_scatter.svg'])

%% lick volume
f = figure(2); theme('light'); clf; hold on;
fig_size = [600,600];
f.Position = [80 80 fig_size];

edges = 0:1:35; % volume in uL
edges = [edges, inf];
histogram(exp_table.lick_vol, edges, "FaceColor",[0,0,0], 'FaceAlpha',1)

xlabel('Lick volume (uL)')
ylabel('Number of sessions')

xline(2, '--', 'LineWidth',3)
xline(25, '--', 'LineWidth',3)
set(gca,'fontsize', 20) 
exportgraphics(gca,['figures', filesep, 'f3_lick_volume.svg'])

