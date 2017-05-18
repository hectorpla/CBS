let test1 = try(drop_last [] = []) with Syn_exn -> true
let test2 = try(drop_last [1;2] = [1]) with Syn_exn -> true
let test3 = try(drop_last [1;2;3] = [1;2]) with Syn_exn -> true
let test4 = try(drop_last [1;2;3;4] = [1;2;3]) with Syn_exn -> true
  
let _ = print_string (string_of_bool (test1 && test2 && test3))
