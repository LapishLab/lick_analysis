function [file_time, file_name] = file_time_for_toi(file_names, time_of_interest)
    file_names = string(file_names);
    file_start = date_from_filename(file_names);
    time_into_file = time_of_interest - file_start;
    time_into_file(time_into_file < 0) = nan; % don't include files that start after time_of_interest
    [file_time, ind] = min(time_into_file); % find the file that started a close to the time_of_interest as possible
    file_name = file_names(ind);
    
    fprintf("file: %s \n", file_name);
    fprintf("time: %s \n", file_time)
end