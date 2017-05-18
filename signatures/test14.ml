let test1 = try(is_palindrome [] = true) with Syn_exn -> true
let test2 = try(is_palindrome [1;2] = false) with Syn_exn -> true
let test3 = try(is_palindrome [1;2;1] = true) with Syn_exn -> true
let test4 = try(is_palindrome [1;2;2;1] = true) with Syn_exn -> true
let test5 = try(is_palindrome [1;3;2;1] = false) with Syn_exn -> true
  
let _ = print_string (string_of_bool (test1 && test2 && test3 && test4 && test5))