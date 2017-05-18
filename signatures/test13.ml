let test1 = try(char_head_of_int_list [] ' ' = ' ') with Syn_exn -> true
let test2 = try(char_head_of_int_list [78;2] ' ' = 'N') with Syn_exn -> true
let test3 = try(char_head_of_int_list [90;2;3] ' ' = 'Z') with Syn_exn -> true
  
let _ = print_string (string_of_bool (test1 && test2 && test3))
