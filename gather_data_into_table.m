clear
folders = dir();
folders = folders(3:end, :); % get rid of . and ..
folders = folders([folders.isdir]); % only include directories

exp_table = table();
for ind = 1:height(folders)
    try
        day_table = load_exp_and_licks(folders(ind).name);
        exp_table = cat(1, exp_table, day_table);
    catch exception
        warning(exception.identifier,'%s \n', exception.message)
        warning('skipping: %s\n', folders(ind).name);
    end
end

save('all_days.mat',"exp_table")

function exp = load_exp_and_licks(folder)
exp = load_exp(folder);
licks = load_licks(folder);
exp.licks = get_licks_for_sippers(exp.sipper, licks);
check_for_unexpected_sippers(exp.sipper, licks);
exp.day(:) = string(folder);
end

function sorted_licks = get_licks_for_sippers(sippers, licks)
sorted_licks = cell(size(sippers));
for ind = 1:length(sippers)
    is_sipper = sippers(ind) == licks.sipper_id;
    is_start = logical(licks.state);
    start = licks.timestamp(is_sipper & is_start);
    stop = licks.timestamp(is_sipper & ~is_start);
    [start,stop] = sanity_check_lick_times(start,stop, sippers(ind));
    if isempty(start)
        sorted_licks{ind} = table(stop, stop); % quick hack to deal with row / column empty issues from removing mismatched start with no stop
    else
        sorted_licks{ind} = table(start, stop);
    end
    sorted_licks{ind} = set_first_lick_as_start(sorted_licks{ind});
end
end

function [start,stop] = sanity_check_lick_times(start,stop, sipper)
    sipper = string(sipper);
    if length(start) > length(stop)
        warning("more starts than stops. Throwing out last start")
        start = start(1:end-1);
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


function exp = load_exp(folder)
    names = {dir(folder).name};
    
    is_exp = strcmp(names, 'experiment_structure.csv');
    if sum(is_exp) == 1
        f_name = [folder, filesep, names{is_exp}];
        exp = readtable(f_name);
    else
        error(['Unexpected number of experiment_structure.csv files in ', folder]);
    end
end

function licks = load_licks(folder)
    names = {dir(folder).name};
    
    is_licks = contains(names, 'licks_');
    if sum(is_licks) == 1
        f_name = [folder, filesep, names{is_licks}];
        licks = readtable(f_name);
    else
        error(['Unexpected number of licks_* files in ', folder]);
    end
end