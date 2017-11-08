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
    
class VarKind(enum.Enum):
    STATIC = 1
    FIELD = 2
    ARG = 3
    VAR = 4

TOKENTYPE_FORMAT = {TokenType.KEYWORD: 'keyword',
                    TokenType.SYMBOL: 'symbol',
                    TokenType.INTEGER: 'integerConstant',
                    TokenType.STRING: 'stringConstant',
                    TokenType.IDENTIFIER: 'identifier'}

SPEICAL_XML_CHAR = {'<': '&lt;',
                    '>': '&gt;',
                    '"': '&quot;',
                    '&': '&amp;'}

SEGMENT_MAP = {VarKind.STATIC: 'static',
               VarKind.FIELD: 'this',
               VarKind.ARG: 'argument',
               VarKind.VAR: 'local'}

OP_TABLE = {'+': 'add', 
            '-': 'sub', 
            '*': 'call Math.multiply 2', 
            '/': 'call Math.divide 2', 
            '&': 'and', 
            '|': 'or', 
            '<': 'lt', 
            '>': 'gt', 
            '=': 'eq'}

UNARY_OP_TABLE = {'-': 'neg', 
                  '~': 'not'}
                    
KEYWORD_CONSTANTS_TABLE = {'true': ('constant', -1), 
                           'false': ('constant', 0), 
                           'null': ('constant', 0), 
                           'this': ('pointer', 0)}

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
            self.current_line = self.current_line.strip()
            # comment in /** */
            # assumes /** always at the beginning of a line
            # and */ always at the end of a line
            if self.current_line.startswith('/**'):
                while not self.current_line.endswith('*/'):
                    self.current_line = self.readinputline().strip()
                self.current_line = self.readinputline()
                # continue to check /** */ patten
                continue
            # comment start with //
            self.current_line = self.current_line.split('//')[0].strip()
            if not self.current_line:  # empty line
                self.current_line = self.readinputline()
            else:  # non-empty line
                break
    
    def advance(self):        
        def isValidChar(c):
            return ('0' <= c <= '9' or 'a' <= c <= 'z' or 'A' <= c <= 'Z' or 
                    c == '_')
        return_token = self.current_token            
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
        return return_token            
        
    def currentToken(self):
        return self.current_token
    
    def tokenType(self):
        return self.current_type
    
    def tokenTypeStr(self):
        return TOKENTYPE_FORMAT[self.current_type]

class CompilationEngine(object):
    
    VARKIND_MAP = {"field": VarKind.FIELD, "static": VarKind.STATIC,
                   "var": VarKind.VAR}
    
    def __init__(self, input_filename, output_filename):
        self.tokenizer = Tokenizer(input_filename)
        self.symbol_table = SymbolTable()
        self.vm_writer = VMWriter(output_filename[:-3]+'vm')
        self.output = open(output_filename, 'w')
        self.if_count = 0
        self.while_count = 0
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
        tokenValue = self.tokenizer.currentToken()
        if tokenValue in SPEICAL_XML_CHAR:
            tokenValue = SPEICAL_XML_CHAR[tokenValue]
        self.writeln(tokenType, tokenValue)     
        if self.tokenizer.hasMoreTokens():
            self.tokenizer.advance()
    
    def compileBracketSyntax(self, func):
        # '(' or '[' or '{'
        self.tokenizer.advance()
        res = func()
        # ')' or ']' or '}'
        self.tokenizer.advance()
        return res
        
    def compileClass(self):
        if self.tokenizer.currentToken() != 'class':
            return False       
        # class keyword
        self.tokenizer.advance()
        # class name, '{'
        self.class_name = self.tokenizer.currentToken()
        for _ in range(2):
            self.tokenizer.advance()
        # variable dec
        while self.compileClassVarDec():
            pass
        # subroutines
        while self.compileSubroutineDec():
            pass
        # '}'
        if self.tokenizer.hasMoreTokens():
            raise Exception(('Expect end of tokens, '
                             'but more tokens are available.'))
        return True
        
    def compileClassVarDec(self):
        if self.tokenizer.currentToken() not in ['static', 'field']:
            return False
        count = 0
        var_kind = self.VARKIND_MAP[self.tokenizer.advance()]        
        var_type = self.tokenizer.advance()       
        while self.tokenizer.tokenType() == TokenType.IDENTIFIER:
            # varName
            var_name = self.tokenizer.advance()
            self.symbol_table.define(var_name, var_type, var_kind)
            count += 1
            if self.tokenizer.currentToken() == ',':
                self.tokenizer.advance()
        # ';'
        self.tokenizer.advance()
        return count       
    
    def compileSubroutineDec(self):
        if self.tokenizer.currentToken() not in ['constructor', 'function',
                                                 'method']:
            return False
        self.symbol_table.startSubroutine()
        subroutine_type = self.tokenizer.advance()
        if subroutine_type == 'method':
            self.symbol_table.define('this', self.class_name, VarKind.ARG)
        # return type
        self.tokenizer.advance()
        # subroutine name
        self.subroutine_name = self.tokenizer.advance()        
        self.compileBracketSyntax(self.compileParameterList)
        self.compileSubroutineBody(subroutine_type) 
        return True    
        
    def compileParameterList(self):
        count = 0
        while (self.tokenizer.tokenType() == TokenType.IDENTIFIER or 
               self.tokenizer.tokenType() == TokenType.KEYWORD):
            var_type = self.tokenizer.advance()
            var_name = self.tokenizer.advance()
            self.symbol_table.define(var_name, var_type, VarKind.ARG)
            count += 1
            if self.tokenizer.currentToken() == ',':
                self.tokenizer.advance()
        return count
        
    def compileSubroutineBody(self, subroutine_type):
        # '{'
        self.tokenizer.advance()
        while self.compileVarDec():
            pass
        func_name = self.class_name + '.' + self.subroutine_name
        local_count = self.symbol_table.varCount(VarKind.VAR)
        self.vm_writer.writeFunction(func_name, local_count)
        if subroutine_type == 'constructor':
            field_count = self.symbol_table.varCount(VarKind.FIELD)
            self.vm_writer.writePush('constant', field_count)
            self.vm_writer.writeCall('Memory.alloc', 1)
            self.vm_writer.writePop('pointer', 0)
        elif subroutine_type == 'method':
            self.vm_writer.writePush('argument', 0)
            self.vm_writer.writePop('pointer', 0)
        self.compileStatements()
        # '}'
        self.tokenizer.advance()
        return True

    def compileVarDec(self):
        if self.tokenizer.currentToken() != 'var':
            return False       
        # kind, type
        var_kind = self.VARKIND_MAP[self.tokenizer.advance()]
        var_type = self.tokenizer.advance()
        while self.tokenizer.tokenType() == TokenType.IDENTIFIER:
            # varName
            var_name = self.tokenizer.advance()
            self.symbol_table.define(var_name, var_type, var_kind)
            if self.tokenizer.currentToken() == ',':
                self.tokenizer.advance()
        # ';'
        self.tokenizer.advance()
        return True

    def compileStatements(self):
        while (self.compileLet() or
               self.compileWhile() or
               self.compileIf() or
               self.compileDo() or
               self.compileReturn()):
            pass
        return True
    
    def compileLet(self):
        if self.tokenizer.currentToken() != 'let':
            return False
        lhs_array = False
        # let
        self.tokenizer.advance()
        lhs = self.tokenizer.advance()
        if self.tokenizer.currentToken() == '[':
            self.vm_writer.writePush(self.symbol_table.KindOf(lhs),
                                     self.symbol_table.IndexOf(lhs))
            lhs_array = True
            self.compileBracketSyntax(self.compileExpression)
            self.vm_writer.writeArithmetic('add')
        # '='
        self.tokenizer.advance()
        self.compileExpression()
        if lhs_array:
            self.vm_writer.writePop('temp', 0)
            self.vm_writer.writePop('pointer', 1)
            self.vm_writer.writePush('temp', 0)
            self.vm_writer.writePop('that', 0)
        else:
            self.vm_writer.writePop(self.symbol_table.KindOf(lhs),
                                    self.symbol_table.IndexOf(lhs))
        # ';'
        self.tokenizer.advance()     
        return True
    
    def compileWhile(self):
        if self.tokenizer.currentToken() != 'while':
            return False
        label_prefix = 'WHILE.'+str(self.while_count)
        self.while_count += 1
        # while
        self.tokenizer.advance()
        # label for start of the while loop
        self.vm_writer.writeLabel(label_prefix+'.L1')
        self.compileBracketSyntax(self.compileExpression)
        self.vm_writer.writeArithmetic('not')
        self.vm_writer.writeIf(label_prefix+'.L2')
        self.compileBracketSyntax(self.compileStatements)
        self.vm_writer.writeGoto(label_prefix+'.L1')
        # label for end of the while loop
        self.vm_writer.writeLabel(label_prefix+'.L2')
        return True
        
    def compileIf(self):
        if self.tokenizer.currentToken() != 'if':
            return False
        label_prefix = 'IF.'+str(self.if_count)
        self.if_count += 1
        # if
        self.tokenizer.advance()
        self.compileBracketSyntax(self.compileExpression)
        self.vm_writer.writeArithmetic('not')
        self.vm_writer.writeIf(label_prefix+'.L1')
        self.compileBracketSyntax(self.compileStatements)
        self.vm_writer.writeGoto(label_prefix+'.L2')
        # label for else statement
        self.vm_writer.writeLabel(label_prefix+'.L1')
        if self.tokenizer.currentToken() == 'else':
            # else
            self.tokenizer.advance()
            self.compileBracketSyntax(self.compileStatements)
        # label for end of if statement
        self.vm_writer.writeLabel(label_prefix+'.L2')
        return True

    def compileSubroutineCall(self, first_name_in=None):
        arg_count = 0
        # subroutine name | className | varName
        first_name = first_name_in or self.tokenizer.advance()
        if self.tokenizer.currentToken() == '(':
            sub_name = self.class_name + '.' + first_name
            # assume function calls are always in the format of XXX.xxx
            arg_count = 1
            self.vm_writer.writePush('pointer', 0)
        elif self.tokenizer.currentToken() == '.':
            # '.'
            self.tokenizer.advance()
            last_name = self.tokenizer.advance()
            if self.symbol_table.hasVar(first_name):
                sub_name = (self.symbol_table.TypeOf(first_name) + '.' +
                            last_name)
                arg_count = 1
                self.vm_writer.writePush(self.symbol_table.KindOf(first_name),
                                         self.symbol_table.IndexOf(first_name))
            else:
                sub_name = first_name + '.' + last_name
            
        arg_count += self.compileBracketSyntax(self.compileExpressionList)
        self.vm_writer.writeCall(sub_name, arg_count)
        
    def compileDo(self):
        if self.tokenizer.currentToken() != 'do':
            return False
        # do
        self.tokenizer.advance()
        self.compileSubroutineCall()
        # pop return value to temp
        self.vm_writer.writePop('temp', 0)
        # ';'
        self.tokenizer.advance()
        return True
    
    def compileReturn(self):
        if self.tokenizer.currentToken() != 'return':
            return False
        # return
        self.tokenizer.advance()
        if not self.compileExpression():
            self.vm_writer.writePush('constant', 0)
        self.vm_writer.writeReturn()
        # ';'
        self.tokenizer.advance()
        return True
        
    def compileExpressionList(self):
        count = 0
        if self.compileExpression():
            count += 1
            while self.tokenizer.currentToken() == ',':
                # ','
                self.tokenizer.advance()
                self.compileExpression()
                count += 1
        return count
    
    def isTerm(self):
        return (self.tokenizer.tokenType() == TokenType.INTEGER or
                self.tokenizer.tokenType() == TokenType.STRING or
                self.tokenizer.tokenType() == TokenType.IDENTIFIER or
                self.tokenizer.currentToken() in KEYWORD_CONSTANTS_TABLE or
                self.tokenizer.currentToken() == '(' or
                self.tokenizer.currentToken() in UNARY_OP_TABLE)
    
    def compileExpression(self):
        if not self.isTerm():
            return False
        self.compileTerm()
        while self.tokenizer.currentToken() in OP_TABLE:
            op = self.tokenizer.advance()
            self.compileTerm()
            self.vm_writer.writeArithmetic(OP_TABLE[op])
        return True        
        
    def compileTerm(self):
        if not self.isTerm():
            return False
        if self.tokenizer.tokenType() == TokenType.INTEGER:
            self.vm_writer.writePush('constant', self.tokenizer.advance())
        elif self.tokenizer.currentToken() in KEYWORD_CONSTANTS_TABLE:
            attr = KEYWORD_CONSTANTS_TABLE[self.tokenizer.advance()]
            self.vm_writer.writePush(attr[0], attr[1])
        elif self.tokenizer.tokenType() == TokenType.STRING:
            str_val = self.tokenizer.advance()
            self.vm_writer.writePush('constant', len(str_val))
            self.vm_writer.writeCall('String.new', 1)
            for c in str_val:
                self.vm_writer.writePush('constant', ord(c))
                self.vm_writer.writeCall('String.appendChar', 2)
        elif self.tokenizer.tokenType() == TokenType.IDENTIFIER:
            first_name = self.tokenizer.advance()
            if self.tokenizer.currentToken() == '[':
                self.vm_writer.writePush(self.symbol_table.KindOf(first_name),
                                         self.symbol_table.IndexOf(first_name))
                self.compileBracketSyntax(self.compileExpression)
                self.vm_writer.writeArithmetic('add')
                self.vm_writer.writePop('pointer', 1)
                self.vm_writer.writePush('that', 0)
            elif self.tokenizer.currentToken() in ['.', '(']:
                self.compileSubroutineCall(first_name)
            else:  # variable
                self.vm_writer.writePush(self.symbol_table.KindOf(first_name),
                                         self.symbol_table.IndexOf(first_name))                
        elif self.tokenizer.currentToken() == '(':
            self.compileBracketSyntax(self.compileExpression)                             
        elif self.tokenizer.currentToken() in UNARY_OP_TABLE:
            op = self.tokenizer.advance()
            self.compileTerm()
            self.vm_writer.writeArithmetic(UNARY_OP_TABLE[op])
        return True


class SymbolTable(object):
    def __init__(self):
        self.class_table = {}
        self.count = {VarKind.STATIC: 0, VarKind.FIELD: 0}
            
    def startSubroutine(self):        
        self.subroutine_table = {}
        self.count.update({VarKind.ARG: 0, VarKind.VAR: 0})            
            
    def define(self, var_name, var_type, var_kind):
        if var_kind in [VarKind.STATIC, VarKind.FIELD]:
            self.class_table[var_name] = (var_type, var_kind, 
                                          self.count[var_kind])            
        else:
            self.subroutine_table[var_name] = (var_type, var_kind, 
                                               self.count[var_kind])
        self.count[var_kind] += 1
    
    def varCount(self, var_kind):
        return self.count[var_kind]
    
    def TypeOf(self, var_name):
        if var_name in self.subroutine_table:
            return self.subroutine_table[var_name][0]
        else:
            return self.class_table[var_name][0]
    
    def KindOf(self, var_name):
        if var_name in self.subroutine_table:
            return self.subroutine_table[var_name][1]
        else:
            return self.class_table[var_name][1]
    
    def IndexOf(self, var_name):
        if var_name in self.subroutine_table:
            return self.subroutine_table[var_name][2]
        else:
            return self.class_table[var_name][2]
    
    def hasVar(self, var_name):
        return (var_name in self.subroutine_table or
                var_name in self.class_table)


class VMWriter(object):
    def __init__(self, output_filename):
        self.output = open(output_filename, 'w')
    
    def writeFunction(self, func_name, n_locals):
        self.output.write('function %s %d\n'%(func_name, n_locals))
    
    def writeCall(self, func_name, n_vars):
        self.output.write('call %s %d\n'%(func_name, n_vars))
        
    def writePush(self, segment, index):
        index = int(index)
        if isinstance(segment, VarKind):
            segment = SEGMENT_MAP[segment]
        self.output.write('push %s %d\n'%(segment, abs(index)))
        if segment == 'constant' and index < 0:
            self.output.write('neg\n')
            
    def writePop(self, segment, index):
        if isinstance(segment, VarKind):
            segment = SEGMENT_MAP[segment]
        self.output.write('pop %s %d\n'%(segment, int(index)))        
        
    def writeArithmetic(self, op):
        self.output.write('%s\n'%op)
        
    def writeReturn(self):
        self.output.write('return\n')
    
    def writeLabel(self, label):
        self.output.write('label %s\n'%label)
    
    def writeIf(self, label):
        self.output.write('if-goto %s\n'%label)
        
    def writeGoto(self, label):
        self.output.write('goto %s\n'%label)
        
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
        outputfile =  '.'.join(inputfile.split('.')[:-1]) + '.xml'
        compilation_engine = CompilationEngine(inputfile, outputfile)
        compilation_engine.compileClass()

    
if __name__ == '__main__':
    main()