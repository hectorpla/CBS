let test1 = try(concat_charlist [] = "") with Syn_exn -> true
let test2 = try(concat_charlist ['1';'2'] = "12") with Syn_exn -> true
let test3 = try(concat_charlist ['a';'b';'c'] = "abc") with Syn_exn -> true

let _ = print_string (string_of_bool (test1 && test2 && test3))
