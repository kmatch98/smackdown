# smackDown.py
# Kevin Matocha - Copyright (C) 2020
# Written for CircuitPython
#
# ################
# Objective: Provide a simple parser and renderer for Markdown text files (.md) with a subset of features,
#           suitable for displaying text on 320x240 pixel LCD displays
#
# Strategy: To reduce memory usage, smackDown only deals with one line at a time.  That means, it does not
# perform any overall-file analysis (table of contents, ordered list depth analysis).  Several state variables
# are used to manage the formatting (located in fontController class):
#   lastFontIndex:in the case a line break is required (such as when encountering a Header).
#   quoteDepth: saves the current quoting level (is reset upon a new section)
#   freshSection: determins if a newSection was just created (to ignore excess newlines)
#
# This code is designed to handle:
# * Headers: Levels 1-6 (using Markdown style headers with '#')
# * Main text: Bold, italic and bold-italic typefaces (3 fonts), with word wrapping
# * Email insets (currently uses '>')
# * TODO: Code blocks: 1 font, monospaced, with background highlighting in grey; no wordrapping only right scrolling
# * TODO: Scrolling navigation using scrolling down (spacebar or arrow keys) and up (arrow keys)
# * TODO: Verify how tabbing works, especially in a code block.
#
# Ignores:
# * Hypertext Links (see note on hard-wrapping of super long lines of text without spaces)
# * Tables
# * RST style headers
# * Strikethrough



# General strategy
# ================
#
# Text Processing Hierarchy
# renderLine - Deals with any line-related features, newlines, etc.
#  -> printText - Breaks line into chunks, including processing any font modifiers.
#       -> wrapAndWriteText - Manages word-wrapping and character by character wrapping for super-long lines
#          -> placeText (from textMap library) - Displays the text on the screen
# Strip the input string into text lines. The lines are sent with the newlines stripped.
# Process a single text line. Note: Blank lines should also be processed.
#
# Check if the line is a newline.  This may create a new section.
# Check the blockQuoteLevel.  Strip quotes from the left and process the rest of the line.
# Check if this is a header.
# Check the tabbing level (will set the indent level of any lists.)
# Start printing some text, looking for any fontModifiers.
# Process one word at a time.  Perform any wordwrapping.
# Text printing uses the current fontModifier to set the font.
#
# Check if anything needs to be reset (due to multiple newlines, header found, etc.)
#
#
# To do:
# Add code blocks with a separate font.
# Document the function handling sequence for strings.
#


# State variables
# ===============
# freshSection: This is set to True when a new section is completed. A section is set to "fresh" whenever
# two or more newlines are found. A freshSection starts with a vertical spacing separation (newSectionYOffset).
#
# quoteDepth: The current e-mail like block quote level, defined by the number of leading '>' marks.
# This mode is cancelled when two or more newlines are found. The quoteDepth is reset to a new level
# whenever any leading '>' marks are found.
#
# tabLevel: Identifies how many leading tabs are observed. The tabLevel sets the depth of any lists.
#
# fontController: Contains a stack of observed text character modifiers for the font (bold, italic).  Modifiers are appended
# whenever they are encountered in a text line.  Modifiers are popped from the stack whenever the corresponding modifier
# characters are observed again to 'close' the modifier. The fontModifiers are reset to [] whenever two newlines are found, or
# if a header is encountered.
# The rendered font should be selected based on the composition of the fontController.
#

# Other "features" that could be improved:
#   If there is a super long line of text without any spaces (e.g. URLs), it is hard-wrapped character by character.  If 
# there are any font formatting elements in the middle of a super long, it will break it into chunks and do a newline. This
# is currently considered a "feature".

import gc
print('Mem free: {}'.format(gc.mem_free()))

# # Setup Fonts
#
# fontList: [header1, header2, header 3, mainTextBold, mainText, mainTextItalic, mainTextBoldItalic]

fontFiles =   [
#            'fonts/BitstreamVeraSans-Roman-32.bdf', # Header1
#            'fonts/BitstreamVeraSans-Roman-24.bdf', # Header2
            'fonts/BitstreamVeraSans-Roman-20.bdf', # Header3
            'fonts/BitstreamVeraSans-Roman-16.bdf', # mainText, Header4+
#            'fonts/Hack-Regular-16.bdf',
#            'fonts/Hack-Bold-16.bdf',
            'fonts/BitstreamVeraSans-Bold-16.bdf', # mainTextBold
            'fonts/BitstreamVeraSans-Oblique-16.bdf',  # mainTextItalic
            'fonts/BitstreamVeraSans-BoldOblique-16.bdf',  # mainTextBoldItalic
            'fonts/TerminusTTF-16.bdf'
            ]

indexHeaders=[0, 2, 3, 1] # Indexes of the header levels # if headerLevel > len(indexHeaders), then use indexMainBody
indexMainBody = 1 # Index of the body text
indexBold=2
indexItalic=3
indexBoldItalic=4
indexCode=5

fontList = []

fontOffsetY = [0, 0, 0, 0, 0, 1] # Offsets the baseline of fonts, down by this many Y pixels relative to 0

# glyphs:
glyphs = b'0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ-,.:?! '

# load all the fonts
print('loading fonts')

from adafruit_bitmap_font import bitmap_font

for i, fontFile in enumerate(fontFiles):
    #print('Processing font {} of {}'.format(i+1,len(fontFiles)))
    fontList.append( bitmap_font.load_font(fontFile) )
    fontList[i].load_glyphs(glyphs) # load the glyphs into memory *** check the amount of memory available *** Trigger an soft error if out of memory.
    #lineWidth=int(fontList[i].get_glyph(ord("M")).height * lineSpacing)
    #print('lineWidth: {}'.format(lineWidth))

# ***** temporary trial

fontHeight=[] # collects the font heights, can be adjusted if required, such as for terminalio.FONT
for index, thisFont in enumerate(fontList):
    fontHeight.append( thisFont.get_glyph(ord("M")).height )
    #print('fontIndex{} height: {}'.format( index, thisFont.get_glyph(ord("M")).height ) )

# Adjust any font heights, if required





# Font Modifiers
# ==============
# Checks for bold and italics
# Contains dictionary of text indicator for bold, italic and bolditalic
# Houses a stack that indicates the current Font Modifiers
#
# functions:
# Search a string for a modifier.  Add modifier to the sttack and split into two halves by the modifier, return both parts to be processed.
# Check if a modifier string matches the last item of the stack and pop it from the stack.
# Parse the stack and identify the current font to be used (normal, bold, italic, bold-italic)
# Reset the stack modifier to empty.

from textmap import placeText, bounding_box, lineSpacingY


class fontController:

    def __init__(self, startX=0, startY=0, sectionGap=4, lineSpacing=1.2, indexMainBody=0):
        self.stack = []
        self.modifierDict = {  #These will be checked for effect from longest to shortest (see leftModifierCheck)
            '___': 'bolditalic',
            '***': 'bolditalic',
            '**' : 'bold',
            '__' : 'bold',
            '*'  : 'italic',
            '_'  : 'italic',
            '\'\'\'' : 'codeBlock',
            '```' : 'codeBlock',
            '`': 'code',

            }
        self.bold = False
        self.italic = False
        self.code = False
        self.codeBlock = False
        self.startX=startX # where to set cursor upon newline
        self.startY=startY # where to set cursor upon new screen
        self.X=startX # X insertion point
        self.Y=startY # Y insertion point
        self.sectionGap=sectionGap # amount of extra spaces for creating a new section
        self.freshSection=True
        self.lineSpacing=lineSpacing 
        self.quoteDepth=0 
        self.lastFontIndex=indexMainBody # this is the index of the last font that was printed

# Getters and setters for insertion point
    def setCursor(self, x, y):
        self.X=x
        self.Y=y

    def setX(self, x):
        self.X=x

    def setY(self, y):
        self.Y=y

    def getCursor(self):
        returnValue = (self.X, self.Y)
        return returnValue

    def getX(self):
        return self.X

    def getY(self):
        return self.Y

    def newSection(self):    # move down the insertionPoint by a sectionGap
        if self.freshSection == True:
            pass
        else:
            insertionY=self.getY()
            self.setCursor( myFontController.startX, insertionY+self.sectionGap )
            self.resetModifier() # since this is a new section, reset the font
            self.quoteDepth=0
            self.freshSection=True # this is a new section


# updateFontStatus: checks the fontModifier stack to determine the current font to use
    def updateFontStatus(self):
        self.bold = False
        self.italic = False
        self.code = False # for inline code or codeBlock
        self.codeBlock = False # use line breaks for each line
        for item in self.stack:
            if self.modifierDict[item] in ['bold', 'bolditalic'] :
                self.bold = True
            if self.modifierDict[item] in ['italic', 'bolditalic']:
                self.italic = True
            if self.modifierDict[item] in ['code', 'codeBlock']:
                self.code = True
            if self.modifierDict[item] in ['codeBlock']:
                self.codeBlock=True


# fontModifierCheck:
# This checks for a key value in a string.  If the key is the leftmost item, it updates the fontModifier stack and return
# the text in two chunks.  The first chunk is ready to print, the remaining chunk needs to be further processed.
#
    # fontModifierCheck: How to use this function
        # run this function on the string and it returns: [firstChunk, key+secondChunk]
        # get the current Font and print the first chunk
        # if key+secondChunk !='': then further process the key+secondChunk
        # else: nothing to do

    def fontModifierCheck(self, text):
        foundaKey=False
        keyIndex=len(text)
        firstKey=''
        firstChunk=''
        secondChunk=''

        for key in sorted(self.modifierDict.keys(), key=len, reverse=True): # check if a key in the string, from longest to shortest
            thisIndex=text.find(key)
            if thisIndex != -1: # the key was found
                if foundaKey == False: # this is the first key found
                    foundaKey = True 
                    keyIndex = thisIndex
                    firstKey = key
                else: # this isn't the first found key
                    if thisIndex < keyIndex: # This key is in an earlier position in the string.
                        keyIndex = thisIndex
                        firstKey = key

        if foundaKey: # found a key
            #print('Found a key')

                [firstChunk, secondChunk]=text.split(firstKey, 1)
                if firstChunk == '': # the key was at the first of the text, check if push or pop
                    #print('top of stack: \'{}\', key: \'{}\''.format(self.stack[-1:], firstKey))
                    
                    returnValue=['', secondChunk] # the firstChunk was empty, so we update the font status and return one string.
                    if len(self.stack) > 0: # the stack is not empty
                        if self.stack[-1] == firstKey: # This key matches the last key, so pop it off
                            self.stack.pop(-1) # It's ok to pop modifiers if in code mode, since it should be a code modifier.
                            self.updateFontStatus()
                            #print('popping Modifier')
                        else: # add this key to the stack.  
                            if self.code == True:
                                returnValue=[firstKey, secondChunk] # this was a code block so send back the key for printing raw
                                pass # If in code mode, can never add modifiers.  But send all the text back!

                            else:
                                self.stack.append(firstKey)
                            #print('adding Modifer 1')
                    else: # it's the first item, so go ahead and add this key to the stack
                        self.stack.append(firstKey)
                        #print('adding Modifier 2')
                    self.updateFontStatus()
                    #returnValue=['', secondChunk] # the firstChunk was empty, so we update the font status and return one string.

                else: # the key was not at the beginning of the line, break it into chunks and return for further processing
                    returnValue=[firstChunk, firstKey+secondChunk]

        else: # No key was found
            returnValue=[text, '']    # No key was found the full line should be sent back to be processed after the text is printed
        #print('bold: {}, italic: {}'.format(self.bold, self.italic))
        return returnValue


    def fontStatus(self): # returns the font status (bold, italic) with two Booleans
        returnValue=(self.bold, self.italic, self.code)
        return returnValue

# resetModifier: clears back to the base font.
    def resetModifier(self):
        self.stack = []
        self.updateFontStatus()


def isNewline(textLine):
    # Accepts a textline and determines if it is only whitespace and a newlines
    # Can use this to check whether to start a new section.
    if len( textLine.strip() )==0:
        return True
    else:
        return False

def findTabLevel(textLine):
    spaceCount=0
    tabLevel=0
    spacesPerTab = 4 # how many spaces equals a tab. should be defined at higher level ****
    for character in textLine:
        if character == '\t': # increase the tab level counter
            spaceCount=0 # reset the space counter to zero
            tabLevel += 1
        elif character == ' ':
            spaceCount += 1 # increase space counter
            if spaceCount >= spacesPerTab: # enough spaces were encountered to equal one tab
                spaceCount=0 # reset the space counter to zero
                tabLevel += 1
        else: # found a character other than a tab or whitespace
            break
    return tabLevel

def blockQuoteLevel(textLine):
    # strip out all the whitespaces
#    print(textLine)
    shrunkText="".join( textLine.split() )
#    print(shrunkText)
#    print(shrunkText.lstrip('>'))
    quoteDepth=len(shrunkText) - len( shrunkText.lstrip('>') )
    return quoteDepth

# Headers
# =======
# This decides what font to used based on the number of Header hashes
#
def isHeader(thisText): # Returns the header depth (0: no Header) and remaining text on the line
    trimmedLine=thisText.lstrip() # trim off any leading whitespace
    noHashLine=trimmedLine.lstrip('#') # trim of any leading hashes ('#' designates a header in Markdown)
    headerDepth=len(trimmedLine)-len(noHashLine) # equals 0 if there are no hashes (use baseline text)
    returnValue=[headerDepth, noHashLine.lstrip()]
    return returnValue

# Unordered List
# ==============
# Determines if an unordered list is found, returns the remaining text, returns a line with leading whitespace trimmed.

bulletStarters = {'* ', '*\t', '- ', '-\t', '+ ', '+\t'} # set of items that indicate the start of a bulleted list

def isUnorderedList(textLine):
    # determines if this line is an unordered list, based on bulletStarters
    # if this isn't a list, return ''
    # if this is a list, just return the remaining text to display
    #
    # Note: Be sure to count the tab level before running this, since leading whitespace is removed.
    #
    trimmedLine=textLine.lstrip()

    if trimmedLine[0:2] in bulletStarters: # this is an unordered list
        returnValue=(True, trimmedLine[2:].lstrip())

    else: # not an unordered list
        returnValue=(False, trimmedLine)
    return returnValue

# Ordered List
# ==============
# Determines if an Ordered list is found, reformats the line with the starting item number.

def isOrderedList(textLine):
    # determines if this list is an ordered list, with a starting number and period.
    #
    # Note: Be sure to count the tab level before running this, since leading whitespace is removed.
    #
    trimmedLine=textLine.lstrip()
    subItems=trimmedLine.split('.', 1) # split off the first number, if present
    if subItems[0].isdigit():
        subItems[0]=subItems[0]+'. ' # add back the period and space to the first element of the list
        subItems[1]=subItems[1].lstrip() # strip any excess whitespace from the first list.
        returnValue=( True, ''.join(subItems) )  # if the first list item is a number, then this must be an ordered list
    else:
        returnValue=( False, trimmedLine )
    return returnValue


def checkLineBreak(textLine):
    # Returns True if a line break is found on this line.
    # In Markdown a line break is defined as two blank spaces before the end of line.
    # This function accepts a single line of text and assumes that newlines are stripped from the textLine.
    # Note: This ignores any tabs at the end of the line.
    textLine=textLine.replace('\t', '') # delete all tabs on this line
    if ( len(textLine) - len(textLine.rstrip(' ')) ) >= 2: # check if 2 spaces are found at the end of the line
        return True
    else:
        return False


#print('\nMem free: {}\n'.format(gc.mem_free()))
#




#################
# Global settings
sectionGap=6  # This is a global setting ***
lineSpacing=1.35 # This is a global setting ***
#backgroundColor=0x000000
lineGapPixels=1  ### Should calculate this based on the lineSpacing
startX=1 # left side margin, where the text begins on the left side
startY=3 # top starting position
displayWidth=320 ## Use this for the display setup

textColor = 0x000000 # Color of the text - black
backgroundColor = 0xBBBB99 # background color
codeBackground = 0xB3B399 # color of background for code **** Not functional - Must add another color to the bitmap palette.

# reset the counters for a new section
#freshSection=True #


myFontController=fontController(startX=startX, startY=startY, 
                                sectionGap=sectionGap, 
                                lineSpacing=lineSpacing,
                                indexMainBody=indexMainBody,
                                )


print ('finished loading fonts')



# insertionPoint(y): y-location of the bottom of the last text printed (y-location in pixels)
insertionPoint = 1 # start at the top (y=0)

#print('Mem free: {}'.format(gc.mem_free()))




from adafruit_display_text import label

def getBodyFont(fontController): # determine the current font based on the fontStatus.  
# 
    (bold, italic, code) = fontController.fontStatus() # get the current body font


    if code:
        returnValue = fontList[indexCode]
    elif (not bold) and (not italic): # bold-italic
        returnValue = fontList[indexMainBody]
    elif bold and (not italic):
        returnValue = fontList[indexBold]
    elif (not bold) and italic:
        returnValue=fontList[indexItalic]
    else: #bold & italic
        returnValue = fontList[indexBoldItalic]
    return returnValue


#############################################
# updated function for displaying a "chunk" of text
# Also manages any text wrapping and fontModifier changes
#####
def printText(thisText, fontIndex, leftMatter, listMatter):
#def printText(thisText, insertionXY, fontIndex, leftMatter, listMatter):

    # leftMatter is printed at the first of each newline (quote block or tabbing level)
    # listMatter is printed only once

    # *** if leftMatter printing is removed below, then this is not needed.
    (insertionX, insertionY) = myFontController.getCursor()

    if thisText != '':
        if fontIndex != None: # must be a header
            font=fontList[fontIndex]
        else: # the font is body text
            # use the font as determined by the fontModifier.
            # call fontModifier Left on this chunk
            # get the current font
            # print the text
            # **At the end, call fontModifer Right on this chun]
            font=fontList[indexMainBody] # temporarily *******

        #print('thisText: \'{}\''.format(thisText) )

        firstText = ''
        secondText = thisText
        # check for any font modifiers
        
        while True:

                (firstText, secondText) = myFontController.fontModifierCheck(secondText) # check for font modifiers.

                if (thisText.strip() == '```') or (thisText.strip() == '\'\'\''): # ignore blank code sections:
                    break
                # fontModifierCheck: How to use this function
                # run this function on the string and it returns: [firstChunk, key+secondChunk]
                # get the current Font and print the first chunk
                # if key+secondChunk !='': then further process the key+secondChunk
                # else: nothing to do
                #print( 'firstText: \'{}\', secondText: \'{}\''.format(firstText, secondText) )
                
                if fontIndex == None: # this is some body text, not a header
                    font=getBodyFont(myFontController) # determine the current body text font, taking into account any modifiers
                if firstText == '' and secondText == '': # nothing left to print
                    break
                if (firstText != ''):
                    #for group in 
                    writeAndWrapText(firstText, font, leftMatter, listMatter, fontList[indexMainBody])
                        #myGroup.append(group)

    #return 



def placeOffsetText(bitmap, text, font, lineSpacing,
                        xPosition, yPosition, 
                        textPaletteIndex=1, 
                        backgroundPaletteIndex=0, 
                        scale=1, 
                    ):

    thisFontYOffset = fontOffsetY[fontList.index(font)] # select the offset from the list of Y-offsets
    offsetInsertionY = yPosition + thisFontYOffset # offsets the baseline position for this font
    (tempInsertionX, tempInsertionY) = placeText(bitmap, text, # Write the character
                                                font, lineSpacing,
                                                xPosition, offsetInsertionY, 
                                                textPaletteIndex, backgroundPaletteIndex, 
                                                scale)

    
    myFontController.setCursor(tempInsertionX, tempInsertionY-thisFontYOffset)
    returnValue = (tempInsertionX, tempInsertionY-thisFontYOffset) # adjust the baseline back
    return returnValue



def writeMatter(text, font): #print something exactly where the cursor is
    (insertionX, insertionY)=myFontController.getCursor()

#       text_Main = label.Label(font = font,
#             text = text,
#             color = textColor,
# #            background_color = backgroundColor,
#             line_spacing = myFontController.lineSpacing,
#             max_glyphs = len(text),
#             x=insertionX,
#             y=insertionY
#         )


    (insertionX, insertionY) = placeOffsetText(color_bitmap, text, 
                                    font, myFontController.lineSpacing,
                                    insertionX, insertionY)

    print('writing left Matter: {}'.format(text))

    #insertionX=insertionX+text_Main.bounding_box[0]+text_Main.bounding_box[2] # update the x-position
    myFontController.setCursor(insertionX, insertionY)
    myFontController.lastFontIndex=fontList.index(font)
    #return text_Main


def writeAndWrapText(text, font, leftMatter, listMatter, matterFont): # Returns a group with the text.  Handles any word wrapping.
    returnValue=[]

    if listMatter != '': # this is an ordered list so make a newline
        lineBreak(myFontController.lastFontIndex)

    (insertionX, insertionY)=myFontController.getCursor()
    #if (insertionX == myFontController.startX) and ((leftMatter + listMatter) != ''):
    #    returnValue.append( writeMatter(leftMatter + listMatter, matterFont) ) # first time to write this line, include the listMatter
    #    (insertionX, insertionY)=myFontController.getCursor() # get the updated cursor position


    myFontController.lastFontIndex=fontList.index(font) # update the lastFont that was used

    # Check the bounding box of the proposed text
    (boundingBoxWidth, boundingBoxHeight)=bounding_box(text, font, myFontController.lineSpacing)


    #print('2x: {}, y: {}, w: {}, h: {}, text.y: {}'.format(bounding_box[0], bounding_box[1], bounding_box[2], bounding_box[3], text_Main.y))

    ###### Any newline needs to start with leftMatter *****  Add print of LeftMatter, be sure to avoid infinite loop.
    if insertionX+boundingBoxWidth > displayWidth:  # This box printed off the right of the screen, move to new line
        #print('Word wrapping')
        #print('add Left Matter: \'{}\''.format(leftMatter))

        #lineYChange=int(font.get_glyph(ord("M")).height*myFontController.lineSpacing) # make a line break
        #fontIndex=fontList.index(font)
        #lineYChange=int(fontHeight[fontIndex]*myFontController.lineSpacing) # make a line break
        lineYChange=lineSpacingY(font, myFontController.lineSpacing)

        #lineYChange=int(text_Main.height * lineSpacing)+lineGapPixels
        if boundingBoxWidth > displayWidth-myFontController.startX: # This is a super long line, perform hard wrapping by character
            # Note: if there are font formatting elements in a super long string, it will be broken into "chunks", so the character
            # wrapping will get interrupted by newlines.  This is left as "feature" for now.
            #print('Found a SUPER-LONG line.')
            # perform hard wrapping character-by-character
            for char in text:
                (boundingBoxWidth, boundingBoxHeight) = bounding_box(char, font, myFontController.lineSpacing)
                #print('insertionX: {}, boundingBoxWidth: {}'.format(insertionX, boundingBoxWidth))
                if insertionX+boundingBoxWidth > displayWidth:  # Needs a newline
                    print('char: {} making a newline'.format(char))
                    myFontController.setX(myFontController.startX)
                    myFontController.setY(insertionY+lineYChange) 
                    (insertionX, insertionY)=myFontController.getCursor()
                    #print('writing newline')
                if (myFontController.getX() == myFontController.startX) and (leftMatter != ''): # first of a line: write leftMatter in newline
                    (insertionX, insertionY) = placeOffsetText(color_bitmap, leftMatter, 
                                font, matterFont, # use the specific font for the leftMatter
                                insertionX, insertionY)
                    myFontController.setCursor(insertionX, insertionY)

                (insertionX, insertionY) = placeOffsetText(color_bitmap, char, # Write the character
                        font, myFontController.lineSpacing,
                        insertionX, insertionY)
                myFontController.setCursor(insertionX, insertionY)

            text='' # clear the text buffer, since it was super-wrapped and printed


        else:
            # Add the left matter to the string and reprint
    #### ****  Change this to check if leftMatter should be printed first
    ##### *** left matter should always be in the indexMainBody font - Need to be printed as a separate group!
            myFontController.setX(myFontController.startX) # start a new line, x position
            myFontController.setY(insertionY+lineYChange) # update the new line, y position
            print('else section Newline')
    if (myFontController.getX() == myFontController.startX): #first of the ine        
        print('WandWT leftMatter: {}, text: {}'.format(leftMatter,text))
        if (leftMatter != ''):
            writeMatter(leftMatter, matterFont) # wrapped, do not include listMatter
        (insertionX, insertionY)=myFontController.getCursor() # get the updated cursor position

            # Move the printed text to the new location
    
    # Updated to use background color for code
    if myFontController.code:
        if (text.strip() == '```') or (text.strip() == '\'\'\''): # ignore these.
            pass
        else:
            print('Code printing: \'{}\''.format(text))
            (insertionX, insertionY) = placeOffsetText(color_bitmap, text, 
                                            font, myFontController.lineSpacing,
                                            insertionX, insertionY, backgroundPaletteIndex=2)
        # use the alternate background color for code
        print('using color for code')
    else: 
        (insertionX, insertionY) = placeOffsetText(color_bitmap, text, 
                                        font, myFontController.lineSpacing,
                                        insertionX, insertionY)

    #(insertionX, insertionY)=placeText(color_bitmap, text, 
    #                            font, myFontController.lineSpacing, 
    #                            insertionX, insertionY)

    #insertionX=insertionX+boundingBoxWidth # update the x-position
    # *** Update calculation of line spacing based on the size of the M-glyph ****

    #gc.collect()

    myFontController.setCursor(insertionX, insertionY)
    #print('writeandWrapText x: {}, y: {}'.format(insertionX, insertionY))

    #returnValue.append(text_Main)
    #return returnValue # returns the group to be printed



def lineBreak(fontIndex):
    #global myFontController
    # ** move this to fontControllerFunction ?  Probably not because it depends on the font height
    #print('lineBreak')
    (insertionX,insertionY)=myFontController.getCursor()
    if insertionX != myFontController.startX:
        myFontController.setCursor( myFontController.startX, insertionY+int(fontHeight[fontIndex]*myFontController.lineSpacing) )
       

###########################
# General strategy
# ================
# Strip the input string into text lines. The lines are sent with the newlines stripped.
# Process a single text line. Note: Blank lines should also be processed.
#
# Check if the line is a newline.  This may create a new section.
# Check the blockQuoteLevel.  Strip quotes from the left and process the rest of the line.
# Check if this is a header.
# Check the tabbing level (will set the indent level of any lists.)
# Start printing some text, looking for any fontModifiers.
# Process one word at a time.  Perform any wordwrapping.
# Text printing uses the current fontModifier to set the font.
#
# Check if anything needs to be reset (due to multiple newlines, header found, etc.)
#
#
# To do:
# If multiple spaces are found, just translate into a single space (but watch out for end of line double spaces to set newline).
#

#####
# define this as a dumbDown Terminal class and have insertionPoint as a class variable
# class variables
# freshSection
# insertionXY
#
# Settings constants:
# ===================
# sectionGap
# lineSpacing
# font lists - add to __init__ function


# This returns a string with the tab level, quote level and the string.
def getLeftMatter(tabLevel, quoteLevel):
    leftMatter=''
    for i in range(tabLevel):
        leftMatter=leftMatter+'   ' # Add tabbing *** tabSpaces
    for i in range(quoteLevel):
        leftMatter=leftMatter+'>' # add quote level *** consider adding a grey box surrounding text line
    return leftMatter

def renderLine(myString):

    myString=myString.rstrip('\n\r')

    #global insertionX, insertionY
    (insertionX, insertionY) = myFontController.getCursor()

    leftMatter='' # left hand text before the main text
    listMatter='' # left hand text related to ordered or unordered list
    thisFontIndex=None # if no change, then print with the mainBody font (with modifiers)

    # Handle a blank newline
    # if it's a newline, and freshSection=True, don't do anything.
    # if it's a newline, and freshSection=False, we just finished up a section, move insertion point down by section distance
    #print('renderLine -> freshSection: {}'.format(myFontController.freshSection))
    if isNewline(myString):
        if (myFontController.freshSection == False):
            if ( myFontController.getX() != myFontController.startX ):
                lineBreak(myFontController.lastFontIndex) #Make a line break.
            myFontController.newSection() # update the insertion point for a new sectionGap
            #print('moving insertion point for new SECTION')
        # else ignore this repeated newline, no need to create a new section.

    else:
        #print('renderLine setting freshSection: FALSE')
        myFontController.freshSection=False
        # process the line and print it


        quoteLevel=blockQuoteLevel(myString) # get the quote level
        if quoteLevel > 1: # only using tabbing if there isn't a quote Block
            tabLevel=findTabLevel(myString) # get the tabbing level
        else: 
            tabLevel=0
        if (quoteLevel != 0) and (quoteLevel != myFontController.quoteDepth): # update the quote Depth if a nonzero level is found.
            myFontController.quoteDepth=quoteLevel
            if insertionX != myFontController.startX: # if this needs a new line add a break
                lineBreak(myFontController.lastFontIndex) # new quote level found, add a line break
                (insertionX, insertionY) = myFontController.getCursor()
            #print('>>>> Changing the quote level >>>>: {}'.format(myFontController.quoteDepth))
        leftMatter=getLeftMatter(tabLevel, myFontController.quoteDepth)
        print('leftMatter: {}, myString: {}'.format(leftMatter, myString))
        #print('tabLevel: {}, quoteLevel: {}'.format(tabLevel, myFontController.quoteDepth))

        # Be sure to print leftMatter first before rendering rest of string.
        # Any leftMatter should be in the base font, never bold or italic
        
        #if leftMatter != '':
            #print( 'leftMatter : \'{}\''.format(leftMatter) )
            #printLeftMatter(leftMatter)
            # update the insertionXandY

        # strip any leading spaces, tabs and any quotes '>' for further processing
        baseString=myString.lstrip(' \t>')
        #baseSTring=myString.rstrip() 

        # Check header
        #print( 'check header: \'{}\''.format(baseString) )
        [headerDepth, trimmedString]=isHeader(baseString)
        if headerDepth > 0: # Just a header, print it
            myFontController.quoteDepth=0 # reset the quote depth
            myFontController.freshSection = True # define this as a new section after a header
            if headerDepth > len(indexHeaders):
                thisFontIndex=indexMainBody # Header is deeper than number of fonts available, use body text
            else:
                thisFontIndex=indexHeaders[headerDepth-1] 
                #print('HeaderFontIndex: {}'.format(thisFontIndex))

            # Adjust the offset of the y-insertion point to make room for the Header

            lineBreak(myFontController.lastFontIndex) # add a line break  
            (insertionX, insertionY)=myFontController.getCursor()
            yOffset = int( fontHeight[thisFontIndex] * myFontController.lineSpacing*1/3 )  # is this right?
            insertionY = insertionY+yOffset
            myFontController.setY(insertionY)
            leftMatter='' # no left matter is printed with a header
            
            #print('HEADER thisFontIndex: {}, yOffset: {}, insertionY: {}'.format(thisFontIndex, yOffset, insertionY))

            #print('Header depth: {} text: \'{}\''.format(headerDepth, trimmedString))
            # print leftMatter with thisFont (send tab Level and quoteLevel)
            # print baseString with thisFont (send tab Level and quoteLevel)  
            # 
            # print with printText loop, but use header Font, need to strip off the header


        else: # it wasn't a header
            #print( 'check ordered list: \'{}\''.format(baseString) )
            [orderedList, trimmedString]=isOrderedList(baseString)
            if orderedList:  # Check for list (ordered or unordered) and print any bullets or counters
                print('Ordered List found, text: \'{}\''.format(trimmedString) )
                # Add the list number text to "listMatter" ****
                # print trimmedString
                listMatter=trimmedString
                pass  # ***** update this?

            else:
                #print( 'check unordered list: \'{}\''.format(baseString) )
                [unOrderedList, trimmedString]=isUnorderedList(baseString)
                if unOrderedList:
                    #print( 'Bullet \'• {}\''.format(trimmedString) )
                    #  ADD a bullet, then print the rest of text, with formatting - Deal with tabbing level above ***
                    # update the insertionXandY
                    listMatter='• '
                    # print trimmedString with base font, send trimmedString, leftMatter and listMatter

                else:
                    #print( 'Normal text \'{}\''.format(baseString) ) # Print with formatting and wordwrapping
                    # update the insertionXandY
                    # print baseString
                    trimmedString=baseString



        # Go print each chunk 
        #print('Go insertionX: {}, insertionY: {}'.format(insertionX, insertionY))
        myFontController.setCursor(insertionX, insertionY)
        for chunk in trimmedString.split(' '):        
            #print('insertionX: {}, insertionY: {}'.format(myFontController.getX(), myFontController.getY()) ) 
            chunk=chunk+' '
            print( 'chunk: \'{}\''.format(chunk) )
            printText(chunk, thisFontIndex, leftMatter, listMatter) # update insertionPoint
            listMatter='' # only print the listMatter once.

        if (headerDepth > 0) or (myFontController.codeBlock):
            # add make a lineBreak if it is a header or code block.
            lineBreak(myFontController.lastFontIndex) 

        elif checkLineBreak(myString): # it is body text, check if the end of string specifies a linebreak
            #print('making a LineBreak...')
            if headerDepth == 0: # if not a header
                lineBreak(myFontController.lastFontIndex)  # do not lineBreak if it is a header


    #print('freshSection: {}'.format(myFontController.freshSection) )



import board
import displayio
import time
import terminalio
import fontio
import sys
import busio
#from adafruit_st7789 import ST7789
from adafruit_ili9341 import ILI9341

print('post imports Mem free: {}'.format(gc.mem_free()))

#  Setup the display

print('Starting the display') # goes to serial only
displayio.release_displays()

spi = board.SPI()
tft_cs = board.D9 # arbitrary, pin not used
tft_dc = board.D10
tft_backlight = board.D12
tft_reset=board.D11

while not spi.try_lock():
    spi.configure(baudrate=32000000)
    pass
spi.unlock()

display_bus = displayio.FourWire(
    spi,
    command=tft_dc,
    chip_select=tft_cs,
    reset=tft_reset,
    baudrate=32000000,
    polarity=1,
    phase=1,
)

print('spi.frequency: {}'.format(spi.frequency))

DISPLAY_WIDTH=320
DISPLAY_HEIGHT=240

#display = ST7789(display_bus, width=240, height=240, rotation=0, rowstart=80, colstart=0)
display = ILI9341(display_bus, width=DISPLAY_WIDTH, height=DISPLAY_HEIGHT, rotation=180, auto_refresh=True)

display.show(None)

print('Display is started.')


myGroup = displayio.Group(max_size=100) # *** may need to make larger

memString='Mem free: {}, lostMem: {}'

lastMem=gc.mem_free()
# Make a background color fill
color_bitmap = displayio.Bitmap(320, 240, 3)
#color_bitmap = displayio.Bitmap(1, 1, 1)

thisMem=gc.mem_free()
print(memString.format(gc.mem_free(), lastMem-thisMem) )
lastMem=thisMem

color_palette = displayio.Palette(3)
color_palette[0] = backgroundColor
color_palette[1] = textColor
color_palette[2] = codeBackground

bg_sprite = displayio.TileGrid(color_bitmap, pixel_shader=color_palette, x=0, y=0)
myGroup.append(bg_sprite)
display.show(myGroup)


thisMem=gc.mem_free()
print(memString.format(gc.mem_free(), lastMem-thisMem) )


#display.auto_refresh=False
display.auto_refresh=True


#process a file


inputFile='README.md'


lineCount=0 


with open(inputFile, 'r') as myFile:
    #print('fileLength: {}'.format(len(myFile)))
    for line in myFile:
        print('len(line): {}'.format(len(line.rstrip('\n\r'))))
        print('lineCount: {}, line: \'{}\''.format(lineCount, line.rstrip('\n\r')))
        renderLine(line)

        lineCount += 1

import time


#print('Time duration: {} sec'.format( (time_end-time_start)/1000 ))

time.sleep(1000000)







