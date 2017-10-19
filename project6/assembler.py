#!/usr/bin/env python3
import copy
import sys

SYM_TABLE_DEFAULT = {'R0': 0, 'R1': 1, 'R2': 2, 'R3': 3, 'R4': 4, 'R5': 5,
                     'R6': 6, 'R7': 7, 'R8': 8, 'R9': 9, 'R10': 10, 'R11': 11,
                     'R12': 12, 'R13': 13, 'R14': 14, 'R15': 15,
                     'SCREEN': 16384, 'KBD': 24576, 'SP': 0, 'LCL': 1,
                     'ARG': 2, 'THIS': 3, 'THAT': 4}

DEST_TABLE = {None: '000', 'M': '001', 'D': '010', 'MD': '011', 'A': '100',
              'AM': '101', 'AD': '110', 'AMD': '111'}

JUMP_TABLE = {None: '000', 'JGT': '001', 'JEQ': '010', 'JGE': '011',
              'JLT': '100', 'JNE': '101', 'JLE': '110', 'JMP': '111'}

CMD_TABLE = {'0': '0101010', '1': '0111111', '-1': '0111010',
             'D': '0001100', 'A': '0110000', '!D': '001101',
             '!A': '0110001', '-D': '0001111', '-A': '0110011',
             'D+1': '0011111', 'A+1': '0110111', 'D-1': '0001110',
             'A-1': '0110010', 'D+A': '0000010', 'D-A': '0010011',
             'A-D': '0000111', 'D&A': '0000000', 'D|A': '0010101',
             'M': '1110000', '!M': '1110001', '-M': '1110011',
             'M+1': '1110111', 'M-1': '1110010', 'D+M': '1000010',
             'D-M': '1010011', 'M-D': '1000111', 'D&M': '1000000',
             'D|M': '1010101'}


class Assembler(object):
  def __init__(self, infile):
    infile = infile.strip()
    self.infile = infile
    self.text, self.outfile = self.ReadFile(infile)
    self.lines = self.text.split('\n')
    self.sym_table = copy.copy(SYM_TABLE_DEFAULT)

  def ReadFile(self, infile):
    assert infile[-4:] == '.asm'
    with open(infile, 'r') as f:
      data = f.read()
    outfile = infile[:-4] + '.hack'
    return data, outfile

  def FirstPass(self):
    line_num = 0
    for line in self.lines:
      line = line.strip()
      if not line or line.startswith('//'):
        continue
      if line.startswith('(') and line.endswith(')'):
        sym = line[1:-1]
        self.sym_table[sym] = line_num
      else:
        line_num += 1

  def SecondPass(self):
    mem_avail = 16
    self.instructions = []
    for line in self.lines:
      # Remove comments
      ind_comment = line.find('//')
      if ind_comment != -1:
        line = line[:ind_comment]
      line = line.strip()
      # Skip empty line and labels
      if not line or line.startswith('('):
        continue
      # A instruction
      if line.startswith('@'):
        sym = line[1:]
        try:
          line_num = int(sym)  # sym is already a number
        except ValueError:
          line_num = self.sym_table.get(sym, None)  # exist in sym table
          if line_num == None:  # first time appear
            line_num = mem_avail
            self.sym_table[sym] = mem_avail
            mem_avail += 1
        bin_num = bin(line_num)[2:]
        instruction = '0'*(16-len(bin_num)) + bin_num
      # D instruction
      else:
        dest = None
        jump = None
        ind_dest = line.find('=')
        if ind_dest != -1:
          dest = line[:ind_dest].strip()
          line = line[ind_dest+1:].strip()
        ind_jump = line.rfind(';')
        if ind_jump != -1:
          jump = line[ind_jump+1:].strip()
          line = line[:ind_jump].strip()
        cmd = line
        instruction = ('111' + CMD_TABLE[cmd] + DEST_TABLE[dest]
                       + JUMP_TABLE[jump])
      # Append instruction
      self.instructions.append(instruction)

  def WriteOutput(self):
    with open(self.outfile, 'w') as f:
      for instruction in self.instructions:
        f.write(instruction)
        f.write('\n')

  def Parse(self):
    self.FirstPass()
    self.SecondPass()
    self.WriteOutput()

def main():
  if len(sys.argv) > 1:
    infile = sys.argv[1]
  else:
    print('Usage: %s inputfile'%sys.argv[0])
    sys.exit(1)
  assembler = Assembler(infile)
  assembler.Parse()

if __name__ == '__main__':
  main()
