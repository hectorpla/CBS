# OCPet

OCPet is a program synthesizer for OCaml language. The idea of OCPet comes from SyPet, a component-based java program synthesizer, with Petri net as the underlying data structure to express search space. 

## Prerequisites
Python3, OCaml, z3, graphviz, tkinter(optional, for GUI)  

## Getting Started
### Mac
1. Install prerequisites  
    1. brew install python3  
    2. brew install graphviz  
    3. pip3 install z3 (might not work)
    4. brew install ocaml (version matters)
2. Simply clone this repository to your desktop.
3. Test (see the Examples session below)

## Directories

### Architecture
```
.  
├─── snakes/  
│    ├─ ...  
│    └─ plugins  
│    	├─ ...  
│    	└─ search.py  
├─── signatures/  
├─── json/  
├─── draws/  
├─── teprog/  
├─── data.py  
├─── synthesis.py  
...
```


### Notes
+ *signatures/* stores signature information (.json files) and tests used to synthesize program.

+ *json/* stores component information (type infos of functions).
 
+ *snakes/* contains the modified SNAKES module, the Petri net implementation.

+ *teprog/* contains signatures of half-completed function and tests for those functions.  

+ *snakes/plugins/search.py* a plug-in added to SNAKES, implementation of algorithms of sketch enumeration.

- *synthesis.py* implementation of algorithms of concrete code geneartion and verification

- *data.py* defines data abstractions used in synthesis.py

## Examples
Modify signature file name to target signature file name, and run the following command in terminal.
```
python3 main.py
```
## Components

Component information is collected from the sources of standard libraries that reside in OCaml installation. The parser is implemented in OCaml, but not in this repository yet.

Included libraries are: char, string, bytes, list.

## References
1. Component-Based Synthesis for Complex APIs, by Yu Feng.
2. Refer to SyPet here: https://github.com/fredfeng/fredfeng.github.io/tree/master/sypet/all-in-one/SyPet
3. Thanks to Franck Pommereau for the SNAKES module. Please refer to https://github.com/fpom/snakes.

