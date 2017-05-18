(* Correct program 
 let myFunc arg0 = 
   arg0
 *)

let test1 = idFunc 'c' 'g' = 'c'
let test2 = idFunc 'F' 'a' = 'F'
  
let _ = print_string (string_of_bool (test1 && test2))
