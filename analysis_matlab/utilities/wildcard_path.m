function file_paths = wildcard_path(search_string)
    matches = dir(search_string);

    if isempty(matches)
        error('No files match the search string: %s', search_string);
    end
    
    file_paths = string({matches.folder}) + filesep + string({matches.name});
end