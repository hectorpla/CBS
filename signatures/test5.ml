let test1 = try(concat_ym '/' "1992" "10" = "1992/10") with Syn_exn -> true
let test2 = try(concat_ym '-' "1983" "1" = "1983-1") with Syn_exn -> true

let _ = print_string (string_of_bool (test1 && test2))