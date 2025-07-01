function err = sem(x)
err = std(x) / sqrt(size(x, 1));
end