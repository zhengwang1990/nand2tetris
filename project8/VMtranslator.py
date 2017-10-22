# -*- coding: utf-8 -*-
"""
Created on Sun Oct 15 19:18:05 2017

@author: zheng
"""
import sys
import enum
import os

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
                      'push': CType.C_PUSH, 'pop': CType.C_POP,
                      'label': CType.C_LABEL,
                      'if-goto': CType.C_IF,
                      'goto': CType.C_GOTO,
                      'function': CType.C_FUNCTION,
                      'call': CType.C_CALL,
                      'return': CType.C_RETURN}
    
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
        return int(self.cmd_list[2])

class CodeWriter(object):
    SEGMENT_TABLE = {'local': 'LCL', 'argument': 'ARG', 'this': 'THIS',
                     'that': 'THAT'}
    def __init__(self, file):
        self.outputfile = file
        self.line_count = 0
        self.function_name = 'null'
        self.return_count = 0
        
    def writeln(self, content):
        self.outputfile.write(content + '\n')
        self.line_count += 1

    def setFileName(self, filename):
        filename = os.path.split(filename)[1]
        self.filename = '.'.join(filename.split('.')[:-1])
    
    def writeInit(self):
        self.writeComments('Initialize')
        self.writeln('@256')
        self.writeln('D=A')
        self.writeln('@SP')
        self.writeln('M=D')
        self.writeCall('Sys.init', 0)
   
    def writeLabel(self, label=None):
        if label:
            label = self.function_name + '$' + label
        else:
            label = self.function_name
        self.writeln('(' + label + ')')
        self.line_count -= 1
        
    def writeIf(self, label):
        label = self.function_name + '$' + label
        self.popD()
        self.writeln('@' + label)
        self.writeln('D; JNE')
        
    def writeGoto(self, label):
        label = self.function_name + '$' + label
        self.writeln('@' + label)
        self.writeln('0; JMP')
    
    def writeFunction(self, func_name, nvars):
        self.function_name = func_name
        self.return_cnt = 0
        self.writeLabel()
        # D=0
        self.writeln('@0')
        self.writeln('D=A')
        for _ in range(nvars):
            self.pushD()
            
    def writeCall(self, func_name, nargs):
        # push return address
        self.return_count += 1
        label = 'ret.' + str(self.return_count)
        self.writeln('@' + self.function_name + '$' + label)
        self.writeln('D=A')
        self.pushD()
        # push LCL, ARG, THIS, THAT
        for saved in ['LCL', 'ARG', 'THIS', 'THAT']:
            self.writeln('@' + saved)
            self.writeln('D=M')
            self.pushD()       
        # ARG=SP-5-nargs
        self.writeln('@SP')
        self.writeln('D=M')
        self.writeln('@5')
        self.writeln('D=D-A')
        self.writeln('@' + str(nargs))
        self.writeln('D=D-A')
        self.writeln('@ARG')
        self.writeln('M=D')        
        # LCL=SP
        self.writeln('@SP')
        self.writeln('D=M')
        self.writeln('@LCL')
        self.writeln('M=D')        
        # go to function
        self.writeln('@' + func_name)
        self.writeln('0; JMP')       
        # function return
        self.writeLabel(label)
    
    def writeReturn(self):
        # endframe = LCL
        self.writeln('@LCL')
        self.writeln('D=M')
        self.writeln('@R13')  # R13=endframe
        self.writeln('M=D')
        self.writeln('@5')
        self.writeln('D=D-A')
        self.writeln('A=D')
        self.writeln('D=M')
        # returnattr = *(endframe-5)
        self.writeln('@R14')  # R14=returnattr
        self.writeln('M=D')
        # *ARG = pop()
        self.popD()
        self.writeln('@ARG')
        self.writeln('A=M')
        self.writeln('M=D')
        # SP = ARG + 1
        self.writeln('D=A')
        self.writeln('@SP')
        self.writeln('M=D+1')
        # restore LCL, ARG, THIS, THAT
        for saved in ['THAT', 'THIS', 'ARG', 'LCL']:
            self.writeln('@R13')
            self.writeln('AM=M-1')
            self.writeln('D=M')
            self.writeln('@' + saved)
            self.writeln('M=D')
        # go to returnattr
        self.writeln('@R14')
        self.writeln('A=M')
        self.writeln('0; JMP')
    
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
    
    def popD(self):
        self.writeln('@SP')
        self.writeln('M=M-1')
        self.writeln('A=M')
        self.writeln('D=M')
    
    def pushD(self):
        self.writeln('@SP')
        self.writeln('A=M')
        self.writeln('M=D')
        self.writeln('@SP')
        self.writeln('M=M+1')
            
    def writePushPop(self, cmd, segment, index):
        seg_pt = self.SEGMENT_TABLE.get(segment, None)
        if cmd == CType.C_PUSH:
            if seg_pt:
                self.writeln('@' + seg_pt)
                self.writeln('D=M')
                self.writeln('@' + str(index))
                self.writeln('A=D+A')
                self.writeln('D=M')             
            elif segment == 'constant':
                self.writeln('@' + str(index))
                self.writeln('D=A')
            elif segment == 'static':
                self.writeln('@' + self.filename + '.' + str(index))
                self.writeln('D=M')
            elif segment == 'temp':
                self.writeln('@' + str(5+index))
                self.writeln('D=M')
            else:  # segment == 'pointer'
                if index == '0':
                    self.writeln('@THIS')
                else:
                    self.writeln('@THAT')
                self.writeln('D=M')
            self.pushD()
        else:  # cmd == CType.C_POP
            if seg_pt:
                self.writeln('@' + str(index))
                self.writeln('D=A')
                self.writeln('@' + seg_pt)
                self.writeln('D=D+M')
                self.writeln('@R13')
                self.writeln('M=D')
                self.popD()                
                self.writeln('@R13')
                self.writeln('A=M')
                self.writeln('M=D')
            elif segment == 'static':
                self.popD()
                self.writeln('@' + self.filename + '.' + str(index))
                self.writeln('M=D')
            elif segment == 'temp':
                self.popD()
                self.writeln('@' + str(5+index))
                self.writeln('M=D')
            else:  # segment == 'pointer'
                self.popD()
                if index == 0:
                    self.writeln('@THIS')
                else:
                    self.writeln('@THAT')
                self.writeln('M=D')
        
    def writeComments(self, comment):
        self.writeln('// ' + comment)
        self.line_count -= 1
        
    def Close(self):
        self.outputfile.close()


def ListVmFile(path):
    ret = []
    if os.path.isfile(path):
        if path.endswith('.vm'):
            ret = [path]
    else:
        files = [os.path.join(path, file) for file in os.listdir(path)]
        for file in files:
            ret.extend(ListVmFile(file))
    return ret


def main():
    if len(sys.argv) < 2:
        print('Usage: %s filename/dirname'%sys.argv[0])
        sys.exit(1)
    inputpath = os.path.relpath(sys.argv[1])
    # get a list of VM files to be parsed
    inputfiles = ListVmFile(inputpath)
    
    if os.path.isfile(inputpath):
        outputfile =  '.'.join(inputpath.split('.')[:-1]) + '.asm'
    else:
        outputfile = os.path.join(inputpath, os.path.split(inputpath)[1]+'.asm')
    out_f = open(outputfile, 'w')
    writer = CodeWriter(out_f)
    has_sys_init = any(['Sys.vm' in inputfile for inputfile in inputfiles])
    if has_sys_init:
        writer.writeInit()
    for inputfile in inputfiles:
        in_f = open(inputfile, 'r')
        parser = Parser(in_f)
        writer.setFileName(inputfile)
        while parser.hasMoreCommands():
            writer.writeComments(parser.current_command)
            ctype = parser.currentCommandType()
            if ctype == CType.C_ARITHMETIC:
                writer.writeArithmetic(parser.arg1())
            elif ctype == CType.C_POP or ctype == CType.C_PUSH :
                writer.writePushPop(ctype, parser.arg1(), parser.arg2())
            elif ctype == CType.C_LABEL:
                writer.writeLabel(parser.arg1())
            elif ctype == CType.C_IF:
                writer.writeIf(parser.arg1())
            elif ctype == CType.C_GOTO:
                writer.writeGoto(parser.arg1())
            elif ctype == CType.C_FUNCTION:
                writer.writeFunction(parser.arg1(), parser.arg2())
            elif ctype == CType.C_CALL:
                writer.writeCall(parser.arg1(), parser.arg2())
            elif ctype == CType.C_RETURN:
                writer.writeReturn()
            else:
                raise NotImplementedError('Command type not implemented!')  
            parser.advance()
        in_f.close()
    writer.Close()

if __name__ == '__main__':
    main()