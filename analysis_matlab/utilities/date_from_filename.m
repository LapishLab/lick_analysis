function t = date_from_filename(f)
    f = string(f); % make sure it is a string for simplicity
    [~,names,~] = fileparts(f);
    num_char = strlength(names);
    
    if all(num_char == 15)
        format = 'yyyyMMdd_HHmmss';
    elseif all(num_char == 22)
        format = 'yyyyMMdd_HHmmss_SSSSSS';
    else
        error('Filenames do not match expected character length.');
    end
    t = datetime(names, InputFormat=format);
end