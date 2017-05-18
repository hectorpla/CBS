let test1 = try(set_char "parellel" 'a' 3 = "parallel") with Syn_exn -> true
let test2 = try(set_char "conviniance" 'e' 4 = "conveniance") with Syn_exn -> true

let _ = print_string (string_of_bool (test1 && test2))