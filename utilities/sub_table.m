function t = sub_table(full_table, column, value)
    if isstring(value) | ischar(value)
        is_match = strcmp(full_table{:,column}, value);
    else
        is_match = full_table{:,column} == value;
    end
    t = full_table(is_match,:);
end