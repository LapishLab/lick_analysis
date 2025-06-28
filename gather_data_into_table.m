clear
folders = dir();
folders = folders(3:end, :); % get rid of . and ..
folders = folders([folders.isdir]); % only include directories

exp_table = table();
for ind = 1:height(folders)
    day_table = load_exp_and_licks(folders(ind).name);
    exp_table = cat(1, exp_table, day_table);
end

save('all_days.mat',"exp_table")

function exp = load_exp_and_licks(folder)
f = [folder, filesep];
exp = readtable([f, 'experiment_structure.csv']);

licks_file = dir([f, 'licks_*.csv']).name;
licks = readtable([f, licks_file]);
exp.licks_L = get_licks_for_sippers(exp.sipper_L, licks);
exp.licks_R = get_licks_for_sippers(exp.sipper_R, licks);
check_for_unexpected_sippers([exp.sipper_R; exp.sipper_L], licks);
exp.day(:) = string(folder);
end

function sorted_licks = get_licks_for_sippers(sippers, licks)
sorted_licks = cell(size(sippers));
for ind = 1:length(sippers)
    is_sipper = sippers(ind) == licks.sipper_id;
    is_start = logical(licks.state);
    start = licks.timestamp(is_sipper & is_start);
    stop = licks.timestamp(is_sipper & ~is_start);
    sanity_check_lick_times(start,stop, sippers(ind))
    sorted_licks{ind} = table(start, stop);
    sorted_licks{ind} = set_first_lick_as_start(sorted_licks{ind});
end
end

function sanity_check_lick_times(start,stop, sipper)
    sipper = string(sipper);
    if length(start) ~= length(stop)
        error("unequal number of lick starts and stops for sipper " + sipper)
    end
    
    duration = stop - start;
    if any(duration<0)
        warning("negative lick duration computer for sipper " + sipper)
    end
    
    max_d = max(duration);
    if max_d>1000
        d = string(max_d);
        warning("suspiciously long lick duration ("+d+") detected for " + sipper)
    end
end

function check_for_unexpected_sippers(expected_sippers, licks)
unexpected = ~any(expected_sippers == licks.sipper_id');
if any(unexpected)
    unexpected_id = unique(licks.sipper_id(unexpected));
    warning("licks recorded for sipper ID not listed in experiment sheet " +   mat2str(unexpected_id))
end
end

function licks = set_first_lick_as_start(licks)
if height(licks)>0
    start_time = licks{1,1};
    licks = licks(2:end,:) - start_time;
end
end