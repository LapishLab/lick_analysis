function t = sub_table(full_table, varargin)
    is_match = true(height(full_table),1);
    for i=1:length(varargin)
        column = varargin{i}{1};
        value = varargin{i}{2};
        if isstring(value) | ischar(value)
            is_match = is_match & strcmp(full_table{:,column}, value);
        else
            is_match = is_match & full_table{:,column} == value;
        end
    end
    t = full_table(is_match,:);
end