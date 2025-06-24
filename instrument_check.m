clear
data_path = dir("*.csv");
lick_table = readtable(data_path.name);

%% Timestamps are increasing
plot(lick_table.timestamp)
is_increasing = diff(lick_table.timestamp) > 0;
if(any(~is_increasing))
    error("Timestamps are not monotonically increasing!!!!")
end

%% Are sipper ID in order
is_increasing = diff(lick_table.sipper_id) >=  0;
if(any(~is_increasing))
    error("Sipper IDs are not monotonically increasing!!!!")
end
%% Does the OFF state always follow an ON state
is_start = lick_table.state == 1;

if sum(is_start) ~= sum(~is_start)
    error("Number of ON states does not equal number of OFF states!!!!")
end

if any(lick_table.sipper_id(is_start) ~= lick_table.sipper_id(~is_start))
    error("sequential start and stop licks do not correspond to the same sipper ID")
end

lick_duration = lick_table.timestamp(~is_start) - lick_table.timestamp(is_start);
if any(lick_duration <= 0)
    error("Lick duration was less than or equal to 0 milliseconds")
end
%% Is there 1 and only 1 instance of each sipper ON/OFF
is_start = lick_table.state == 1;


if check_for_sipper_repeats(lick_table.sipper_id(is_start))
    error("sipper ON occurs more than once for some sipper")
end
if check_for_sipper_repeats(lick_table.sipper_id(~is_start))
    error("sipper OFF occurs more than once for some sipper")
end

function repeats = check_for_sipper_repeats(sippers)
    unique_sip_starts = unique(sippers);
    repeats = length(unique_sip_starts) ~= length(sippers);
end


disp("Success")