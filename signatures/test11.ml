let test1 = try(head_of_list [] 0 = 0) with Syn_exn -> true
let test2 = try(head_of_list [1;2] 0 = 1) with Syn_exn -> true
let test3 = try(head_of_list [5;2;3] 0 = 5) with Syn_exn -> true
  
let _ = print_string (string_of_bool (test1 && test2 && test3))
