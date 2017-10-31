# -*- coding: utf-8 -*-
"""
Created on Sun Oct 29 18:53:46 2017

@author: zheng
"""

import sys
import enum
import os

class TokenType(enum.Enum):
    KEYWORD = 1
    SYMBOL = 2
    INTEGER = 3
    STRING = 4
    IDENTIFIER = 5

TOKENTYPE_FORMAT = {TokenType.KEYWORD: 'keyword',
                    TokenType.SYMBOL: 'symbol',
                    TokenType.INTEGER: 'integerConstant',
                    TokenType.STRING: 'stringConstant',
                    TokenType.IDENTIFIER: 'identifier'}

SPEICAL_XML_CHAR = {'<': '&lt;',
                    '>': '&gt;',
                    '"': '&quot;',
                    '&': '&amp;'}
                    
def xmlLabel(value, is_end=False, indent=0):
    if is_end:
        prefix = '</'
    else:
        prefix = '<'
    return ' '*indent + prefix + value + '>'
    
class Tokenizer(object):
    
    KEYWORD_LIST = ['class', 'constructor', 'function', 'method', 'field', 
                    'static', 'var', 'int', 'char', 'boolean', 'void', 'true',
                    'false', 'null', 'this', 'let', 'do', 'if', 'else',
                    'while', 'return']
    
    SYMBOL_LIST = ['{', '}', '(', ')', '[', ']', '.', ',', ';', '+', '-', '*',
                   '/', '&', '|', '<', '>', '=', '~']
    
    def __init__(self, input_filename, output_filename=None):
        self.input = open(input_filename, 'r')
        self.current_words = []
        self.current_token = None
        self.current_type = None
        self.current_line = None
        self.output = None       
        if output_filename:
            self.output = open(output_filename, 'w')
            self.output.write(xmlLabel('tokens'))
            self.output.write('\n')
        self.readline()
        self.advance()
        
    def hasMoreTokens(self):
        return bool(self.current_line)
    
    def readinputline(self):
        line = self.input.readline()
        if not line:
            self.input.close()
            if self.output: 
                self.output.write(xmlLabel('tokens', True))
                self.output.close()          
        return line
    
    def readline(self):        
        self.current_line = self.readinputline()
        while self.current_line:
            # comment in /** */
            self.current_line = self.current_line.lstrip()
            if self.current_line.startswith('/**'):
                while '*/' not in self.current_line:
                    self.current_line = self.readinputline()
                pos = self.current_line.find('*/')
                self.current_line = self.current_line[pos+2:].strip()
                if not self.current_line:
                    self.current_line = self.readinputline()
                # continue to check /** */ patten
                continue
            # comment start with //
            self.current_line = self.current_line.split('//')[0]
            self.current_line = self.current_line.strip()
            if not self.current_line:  # empty line
                self.current_line = self.readinputline()
            else:  # non-empty line
                break
    
    def advance(self):        
        def isValidChar(c):
            return ('0' <= c <= '9' or 'a' <= c <= 'z' or 'A' <= c <= 'Z' or 
                    c == '_')
                    
        line = self.current_line  # alias copy
        token_len = 1
        if '0' <= line[0] <= '9':  # integer constant            
            while token_len < len(line) and '0' <= line[token_len] <= '9':
                token_len += 1
            self.current_type = TokenType.INTEGER
            self.current_token = line[:token_len]
        elif line[0] == '"':  # string constant
            while token_len < len(line) and line[token_len] != '"':
                token_len += 1
            self.current_type = TokenType.STRING
            self.current_token = line[1:token_len]
            token_len += 1
        elif line[0] in self.SYMBOL_LIST:
            self.current_type = TokenType.SYMBOL
            self.current_token = line[0]
        else:  # identifier or keywords
            while token_len < len(line) and isValidChar(line[token_len]):
                token_len += 1
            self.current_token = line[:token_len]
            if self.current_token in self.KEYWORD_LIST:
                self.current_type = TokenType.KEYWORD
            else: 
                self.current_type = TokenType.IDENTIFIER   
        
        if self.output:
            label = self.tokenTypeStr()
            self.output.write(xmlLabel(label)+' ')
            if self.current_token in SPEICAL_XML_CHAR:
                self.output.write(SPEICAL_XML_CHAR[self.current_token])
            else:
                self.output.write(self.current_token)
            self.output.write(' '+xmlLabel(label,True))
            self.output.write('\n')
        
        self.current_line = line[token_len:].lstrip()
        if not self.current_line:
            self.readline()            
        
    def currentToken(self):
        return self.current_token
    
    def tokenType(self):
        return self.current_type
    
    def tokenTypeStr(self):
        return TOKENTYPE_FORMAT[self.current_type]

class CompilationEngine(object):
    def __init__(self, input_filename, output_filename):
        self.tokenizer = Tokenizer(input_filename)
        self.output = open(output_filename, 'w')
        self.indent = 0
    
    def writeln(self, label, value=None, is_end=False):
        if value:
            self.output.write(xmlLabel(label, False, self.indent)+' ')
            self.output.write(value)
            self.output.write(' '+xmlLabel(label, True, 0))
        else:
            self.output.write(xmlLabel(label, is_end, self.indent))
        self.output.write('\n')
    
    def writeToken(self, tokenType=None):
        tokenType = tokenType or self.tokenizer.tokenTypeStr()
        self.writeln(tokenType, self.tokenizer.currentToken())       
        self.tokenizer.advance()
        
    def compileClass(self):
        if self.tokenizer.currentToken() != 'class':
            return False
        
        self.writeln('class', is_end=False)
        self.indent += 2
        # class keyword, class name, '{'
        for _ in range(3):
            self.writeToken()
        # variable dec
        self.compileClassVarDec()
        # subroutines
        while self.compileSubroutineDec():
            pass
        self.indent -= 2
        self.writeln('class', is_end=False)
        
        return True
        
    def compileClassVarDec(self):
        pass
    
    def compileSubroutineDec(self):
        if self.tokenizer.currentToken() not in ['constructor', 'function',
                                                 'method']:
            return False
        
        self.writeln('subroutineDec', is_end=False)
        self.indent += 2
        # subroutine type, return type, subroutine name, '('
        for _ in range(4):
            self.writeToken()
        self.compileParameterList()
        # ')'
        self.writeToken()
        self.compileSubroutineBody()
        self.indent -= 2
        self.writeln('subroutineDec', is_end=True)
        
        return True    
        
    def compileParameterList(self):
        self.writeln('parameterList', is_end=False)
        self.indent += 2
        while (self.tokenizer.tokenType() == TokenType.IDENTIFIER or 
               self.tokenizer.tokenType() == TokenType.KEYWORD):
            for _ in range(2):
                self.writeToken()
            if self.tokenizer.currentToken() == ',':
                self.writeToken()
        self.indent -= 2
        self.writeln('parameterList', is_end=True)
        return True
        
    def compileSubroutineBody(self):
        self.writeln('subroutineBody', is_end=False)
        self.indent += 2
        # '{'
        self.writeToken()
        while self.compileVarDec():
            pass
        self.compileStatements()
        self.indent -= 2
        self.writeln('subroutineBody', is_end=True)
        return True

    def compileVarDec(self):
        if self.tokenizer.currentToken() != 'var':
            return False
        
        self.writeln('varDec', is_end=False)
        self.indent += 2
        # var
        self.writeToken()
        while (self.tokenizer.tokenType() == TokenType.IDENTIFIER or 
               self.tokenizer.tokenType() == TokenType.KEYWORD):
            self.writeToken()
            if self.tokenizer.currentToken() == ',':
                self.writeToken()
        # ';'
        self.writeToken()
        self.indent -= 2
        self.writeln('varDec', is_end=True)
        return True

    def compileStatements(self):
        self.writeln('statements', is_end=False)
        self.indent += 2
        while (self.compileLet()):
            pass
        self.indent -= 2
        self.writeln('statements', is_end=True)
        return True
    
    def compileLet(self):
        if self.tokenizer.currentToken() != 'let':
            return False
        # let, var
        for _ in range(2):
            self.writeToken()
        if self.tokenizer.currentToken() == '[':
            raise NotImplemented('Expression')
        # '='
        self.writeToken()
    
def ListJackFile(path):
    ret = []
    if os.path.isfile(path):
        if path.endswith('.jack'):
            ret = [path]
    else:
        files = [os.path.join(path, file) for file in os.listdir(path)]
        for file in files:
            ret.extend(ListJackFile(file))
    return ret

def main():
    if len(sys.argv) < 2:
        print('Usage: %s filename/dirname'%sys.argv[0])
        sys.exit(1)
    inputpath = os.path.relpath(sys.argv[1])
    # get a list of Jack files to be parsed
    inputfiles = ListJackFile(inputpath)
    
    for inputfile in inputfiles:
        outputfile =  '.'.join(inputfile.split('.')[:-1]) + 'T.xml'
        tokenizer = Tokenizer(inputfile, outputfile)
        while tokenizer.hasMoreTokens():
            tokenizer.advance()
            
    for inputfile in inputfiles:
        outputfile =  '.'.join(inputfile.split('.')[:-1]) + '.xml'
        compilation_engine = CompilationEngine(inputfile, outputfile)
        compilation_engine.compileClass()
    
if __name__ == '__main__':
    main()