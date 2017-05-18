let test1 = try(concat_ymd '/' "1992" "10" "2" = "1992/10/2") with Syn_exn -> true
let test2 = try(concat_ymd '-' "1983" "1" "31" = "1983-1-31") with Syn_exn -> true

let _ = print_string (string_of_bool (test1 && test2))