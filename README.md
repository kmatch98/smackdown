# CircuitPython Library: textMap

## What it does
Memory-conserving text graphics handling for CircuitPython, including colored text boxes.




## Usage
'''
    import textmap
    from textmap import textBox
'''

This set of text display routines attempts to overcome the large memory usage of the current "label" function in the 
`CircuitPython_Display_Text` library.  That function uses a collection of tileGrid (one per character) 