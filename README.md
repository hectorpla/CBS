# OCPet

OCPet is a program synthesizer for OCaml language. The idea of OCPet comes from SyPet, a component-based java program synthesizer, with Petri net as the underlying data structure to express search space. 

## Getting Started

Simply clone this repository to your desktop.

### Prerequisites
Python3, z3, dot(optional, for drawing graphs), tkinter(optional, for GUI)

## Directories

+ *signatures/* stores signature information (.json files) and tests used to synthesize program.
 
+ *json/ stores* component information (type infos of functions).
 
+ *snakes/ contains* the modified SNAKES module, the Petri net implementation.
 
## Examples
Modify signature file name to target signature file name, and run the following command in terminal.
```
python3 main.py
```
## Components

Component information is collected from the sources of standard libraries that reside in OCaml installation. The parser is implemented in OCaml, but not in this repsitory yet.

Included libraries are: char, string, bytes, list.

## References
1. Component-Based Synthesis for Complex APIs, by Yu Feng.
2. Refer to SyPet here: https://github.com/fredfeng/fredfeng.github.io/tree/master/sypet/all-in-one/SyPet
3. Thanks to Franck Pommereau for the SNAKES module. Please refer to https://github.com/fpom/snakes.

