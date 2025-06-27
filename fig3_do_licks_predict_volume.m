clear
load("all_days.mat")
 
%% obtain Licks and Volume consumed for alcohol
exp_table = sortrows(exp_table,"consumed_R", "ascend");
alc_volume = exp_table.consumed_R;
alc_licks = exp_table.lickometer == 1;
 
%% obtain licks and volume consumed for water
exp_table = sortrows(exp_table,"consumed_L","ascend");
water_volume = exp_table.consumed_L;



%% david's quick and dirty
figure(2); clf; hold on;
scatter(cellfun(@height, exp_table.licks_R), exp_table.consumed_R , 'filled')
scatter(cellfun(@height, exp_table.licks_L), exp_table.consumed_L , 'filled')
xlabel('Total licks')
ylabel('Total consumed (ml')
legend('ethanol','water')