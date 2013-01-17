#!/usr/bin/python

import sys
import string

class Symbol:
  LPAREN = 0
  RPAREN = 1
  STRING = 2
  NUMBER = 3
  SYMBOL = 4
  WSPACE = 5
  def __init__(self, tag, value=None):
    self.tag = tag
    self.value = value
  def __repr__(self):
    return '<%d: %s>' % (self.tag, self.value)

class Reader:
  def __init__(self, strm):
    self.stream = strm
    self.nxt()
  def peek(self):
    return self.ch
  def nxt(self):
    self.ch = self.stream.read(1)
    return self.ch

class LexerException(Exception):
  pass

class Lexer:
  def __init__(self, strm=sys.stdin):
    self.rdr = Reader(strm)
  def token(self):
    r = self.rdr
    c = r.peek()
    if not c:
      return None
    elif c == '(':
      r.nxt()
      return Symbol(Symbol.LPAREN)
    elif c == ')':
      r.nxt()
      return Symbol(Symbol.RPAREN)
    elif c == '"':
      r.nxt()
      return Symbol(Symbol.STRING, self.readstr())
    elif c in string.digits:
      return Symbol(Symbol.NUMBER, self.readnum())
    elif c in string.ascii_letters or c in '!?%*+-.:<=>^_~':
      return Symbol(Symbol.SYMBOL, self.readsym())
    elif c in string.whitespace:
      self.skipws()
      return self.token()
  def tokens(self):
    while True:
      tok = self.token()
      if not tok:
        break
      else:
        yield tok
  def skipws(self):
    r = self.rdr
    while r.peek() and r.peek() in string.whitespace:
      r.nxt()
  def readstr(self):
    r = self.rdr
    s = ''
    while r.peek() != '"':
      if not r.peek():
        raise LexerException, "Unexpected EOF"
      s += r.peek()
      r.nxt()
    r.nxt()
    return s
  def readnum(self):
    r = self.rdr
    i = ''
    while r.peek() and r.peek() in string.digits:
      i += r.peek()
      r.nxt()
    return i
  def readsym(self):
    r = self.rdr
    c = string.ascii_letters + string.digits + '!?%*+-.:<=>^_~'
    s = r.peek()
    r.nxt()
    while r.peek() and r.peek() in c:
      s += r.peek()
      r.nxt()
    return s

class Parser:
  def __init__(self, lex):
    self.lexer = lex

lex = Lexer()
#toks = list(lex.tokens())
#print toks

class Env:
  def __init__(self, parent=None):
    self.parent = parent
    self.bindings = {}
  def get(self, key):
    if self.bindings.has_key(key):
      return self.bindings[key]
    elif self.parent:
      return self.parent.get(key)
    else:
      raise KeyError, key
  def set(self, key, value):
    self.bindings[key] = value
