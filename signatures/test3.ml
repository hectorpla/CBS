(* let myFunc arg0 arg1 =
  let v0 = String.length arg0 in
  let v1 = Char.chr v0 in
  let _ = String.set arg1 v0 v1 in
arg1
 *)

let test1 = myFunc "kkk" "lllll" = "lll\003l"
let test2 = myFunc "llll" "1234567" = "1234\00467"
  
let _ = print_string (string_of_bool (test1 && test2))
