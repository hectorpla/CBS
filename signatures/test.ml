(* Correct program 
 let myFunc arg0 = 
   let v0 = Char.escaped arg0 in
   v0
 *)

let test1 = to_string 'c' = "c"
let test2 = to_string 'F' = "F"
  
let _ = print_string (string_of_bool (test1 && test2))
