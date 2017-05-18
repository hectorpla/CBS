(* let make_string num c = 
  let v0 = String.make num c in
  let v1 = (^) v0 v0 in
  v1
 *)

let test1 = make_string 1 'k' = "kk"
let test2 = make_string 10 'm' = "mmmmmmmmmmmmmmmmmmmm"
  
let _ = print_string (string_of_bool (test1 && test2))
