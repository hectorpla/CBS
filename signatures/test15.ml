let test1 = try(stutter [] = []) with Syn_exn -> true
let test2 = try(stutter [1] = [1;1]) with Syn_exn -> true
let test3 = try(stutter [1;2] = [1;1;2;2]) with Syn_exn -> true

let _ = print_string (string_of_bool (test1 && test2 && test3))
