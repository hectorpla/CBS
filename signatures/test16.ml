let test1 = try(nth [] 0 = 0) with Syn_exn -> true (* define empty-list behavior *)
let test2 = try(nth [1;2;3;4;5] 3 = 2) with Syn_exn -> true
let test3 = try(nth [9;8;7;6;5;4;3;2;1] 1 = 8) with Syn_exn -> true

let _ = print_string (string_of_bool (test1 && test2 && test3))