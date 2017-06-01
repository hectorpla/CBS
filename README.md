# OCPet

OCPet is a program synthesizer for OCaml language.

## Getting Started

Clone this repository to your desktop.

### Prerequisites
Python3, z3, tkinter(optional)

## Directories

 signatures/ stores signature information (.json files) and tests used to synthesize program.
 
 json/ stores component information (type infos of functions).
 
 snakes/ contains the modified SNAKES module, the Petri net implementation.
## Examples
Modify signature file name to target signature file name, and run the following command in terminal.
```
python3 main.py
```

## Acknowledgments
Thanks to Franck Pommereau for the SNAKES module. Please refer to https://github.com/fpom/snakes.
