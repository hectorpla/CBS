let rec f lst : int list = match lst with
|[] -> []
|fst::rest -> (fst * fst) :: ??
in
print_string (string_of_bool (f [1;2] = [1;4]))