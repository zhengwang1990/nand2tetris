# -*- coding: utf-8 -*-
"""
Created on Sun Oct 15 19:18:05 2017

@author: zheng
"""
import sys
import enum

class CType(enum.Enum):
    C_ARITHMETIC = 1
    C_PUSH = 2
    C_POP = 3
    C_LABEL = 4
    C_GOTO = 5
    C_IF = 6
    C_FUNCTION = 7
    C_RETURN = 8
    C_CALL = 9

class Parser(object):
    CMD_TYPE_TABLE = {'add': CType.C_ARITHMETIC,  'sub': CType.C_ARITHMETIC,
                      'eq': CType.C_ARITHMETIC, 'lt': CType.C_ARITHMETIC,
                      'gt': CType.C_ARITHMETIC, 'neg': CType.C_ARITHMETIC,
                      'and': CType.C_ARITHMETIC, 'or': CType.C_ARITHMETIC,
                      'not': CType.C_ARITHMETIC,
                      'push': CType.C_PUSH, 'pop': CType.C_POP}
    
    def __init__(self, file):
        self.file = file
        self.advance()  # read first line or EOF       
    
    def hasMoreCommands(self):
        return self.current_command
                
    def advance(self):
        self.current_command = self.file.readline()
        while self.current_command:      
            self.current_command = self.current_command.split('//')[0]
            self.current_command = self.current_command.strip()
            if not self.current_command:  # empty line
                self.current_command = self.file.readline()
            else:  # non-empty line
                break
        self.cmd_list = self.current_command.split()
            
    def currentCommandType(self): 
        return self.CMD_TYPE_TABLE[self.cmd_list[0]]
        
    def arg1(self):
        if self.currentCommandType() == CType.C_ARITHMETIC:
            return self.cmd_list[0]
        return self.cmd_list[1]
    
    def arg2(self):
        return self.cmd_list[2]

class CodeWriter(object):
    SEGMENT_TABLE = {'local': 'LCL', 'argument': 'ARG', 'this': 'THIS',
                     'that': 'THAT'}
    def __init__(self, file):
        self.file = file
        filename = file.name.split('/')[-1]
        self.filebase = '.'.join(filename.split('.')[:-1])
        self.line_count = 0
        
    def writeln(self, content):
        self.file.write(content + '\n')
        self.line_count += 1

    def writeArithmetic(self, cmd):
        if cmd in ['not', 'neg']:
            self.writeln('@SP')
            self.writeln('A=M-1')
            if cmd == 'not':
                self.writeln('M=!M')
            else:  # cmd == 'neg'
                self.writeln('M=-M')
            return
        
        self.writeln('@SP')
        self.writeln('M=M-1')
        self.writeln('A=M')
        self.writeln('D=M')
        self.writeln('A=A-1')
        if cmd == 'add':
            self.writeln('M=D+M')
        elif cmd == 'sub':
            self.writeln('M=M-D')
        elif cmd == 'and':
            self.writeln('M=D&M')
        elif cmd == 'or':
            self.writeln('M=D|M')
        elif cmd in ['eq', 'lt', 'gt']:
            self.writeln('D=M-D')
            self.writeln('@' + str(self.line_count+7))
            if cmd == 'eq':
                self.writeln('D; JEQ')
            elif cmd == 'lt':
                self.writeln('D; JLT')
            else:  # cmd == 'gt'
                self.writeln('D; JGT')
            self.writeln('@SP')
            self.writeln('A=M-1')
            self.writeln('M=0')
            self.writeln('@' + str(self.line_count+5))
            self.writeln('0; JMP')
            self.writeln('@SP')
            self.writeln('A=M-1')
            self.writeln('M=-1')
    
    def writePushPop(self, cmd, segment, index):
        def pushD():
            self.writeln('@SP')
            self.writeln('A=M')
            self.writeln('M=D')
            self.writeln('@SP')
            self.writeln('M=M+1')
            
        def popD():
            self.writeln('@SP')
            self.writeln('M=M-1')
            self.writeln('A=M')
            self.writeln('D=M')
            
        seg_pt = self.SEGMENT_TABLE.get(segment, None)
        if cmd == CType.C_PUSH:
            if seg_pt:
                self.writeln('@' + seg_pt)
                self.writeln('D=M')
                self.writeln('@' + index)
                self.writeln('A=D+A')
                self.writeln('D=M')
                pushD()
            elif segment == 'constant':
                self.writeln('@' + index)
                self.writeln('D=A')
                pushD()
            elif segment == 'static':
                self.writeln('@' + self.filebase + '.' + index)
                self.writeln('D=M')
                pushD()
            elif segment == 'temp':
                self.writeln('@' + str(5+int(index)))
                self.writeln('D=M')
                pushD()
            else:  # segment == 'pointer'
                if index == '0':
                    self.writeln('@THIS')
                else:
                    self.writeln('@THAT')
                self.writeln('D=M')
                pushD()
        else:  # cmd == CType.C_POP
            if seg_pt:
                self.writeln('@' + index)
                self.writeln('D=A')
                self.writeln('@' + seg_pt)
                self.writeln('D=D+M')
                self.writeln('@R13')
                self.writeln('M=D')
                popD()                
                self.writeln('@R13')
                self.writeln('A=M')
                self.writeln('M=D')
            elif segment == 'static':
                popD()
                self.writeln('@' + self.filebase + '.' + index)
                self.writeln('M=D')
            elif segment == 'temp':
                popD()
                self.writeln('@' + str(5+int(index)))
                self.writeln('M=D')
            else:  # segment == 'pointer'
                popD()
                if index == '0':
                    self.writeln('@THIS')
                else:
                    self.writeln('@THAT')
                self.writeln('M=D')
        
    def writeComments(self, comment):
        self.writeln('// ' + comment)
        self.line_count -= 1
        
    def Close(self):
        self.file.close()

def main():
    if len(sys.argv) < 2:
        print('Usage: %s filename'%sys.argv[0])
        sys.exit(1)
    inputfile = sys.argv[1]
    in_f = open(inputfile, 'r')
    parser = Parser(in_f)
    outputfile = '.'.join(inputfile.split('.')[:-1]) + '.asm'
    out_f = open(outputfile, 'w')
    writer = CodeWriter(out_f)
    while parser.hasMoreCommands():
        writer.writeComments(parser.current_command)
        ctype = parser.currentCommandType()
        if ctype == CType.C_ARITHMETIC:
            writer.writeArithmetic(parser.arg1())
        else:
            writer.writePushPop(ctype, parser.arg1(), parser.arg2())
        parser.advance()
    writer.Close()
    in_f.close()
    

if __name__ == '__main__':
    main()