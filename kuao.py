#!/usr/bin/python

import sys
import string

class Symbol:
  LPAREN = 0
  RPAREN = 1
  STRING = 2
  NUMBER = 3
  SYMBOL = 4
  def __init__(self, tag, value=None):
    self.tag = tag
    self.value = value
  def __str__(self):
    if self.tag == self.STRING:
      return '"' + self.value + '"'
    elif self.tag == self.SYMBOL:
      return self.value
    elif self.tag == self.NUMBER:
      return str(self.value)
  def __repr__(self):
    if self.value:
      return '%d(%s)' % (self.tag, self.value)
    else:
      return '%d' % (self.tag,)

def listp(e):
  return isinstance(e, list)
def symbolp(e):
  return e.tag == Symbol.SYMBOL
def stringp(e):
  return e.tag == Symbol.STRING
def numberp(e):
  return e.tag == Symbol.NUMBER

class Reader:
  def __init__(self, strm):
    self.stream = strm
    self.ch = None
    #self.nxt()
  def peek(self):
    if self.ch == None:
      self.nxt()
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
    elif c in string.ascii_letters or c in '!?%*+-.:<=>^_~/\\':
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
    esc = {
      '"': '"',
      'n': '\n',
      'r': '\r',
      'f': '\f'
    }
    r = self.rdr
    s = ''
    while r.peek() != '"':
      if not r.peek():
        raise LexerException, "unexpected EOF"
      if r.peek() == '\\':
        # Escape code \n \r \f etc
        r.nxt()
        if r.peek() not in esc:
          raise LexerException, "unknown escape code %s" % (r.peek(),)
        else:
          s += esc[r.peek()]
          r.nxt()
          continue
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
    return int(i)
  def readsym(self):
    r = self.rdr
    c = string.ascii_letters + string.digits + '!?%*+-.:<=>^_~/\\'
    s = r.peek()
    r.nxt()
    while r.peek() and r.peek() in c:
      s += r.peek()
      r.nxt()
    return s

class ParserException(Exception):
  pass

class Parser:
  def __init__(self, lex):
    self.lexer = lex
  def read(self):
    tok = self.lexer.token()
    if not tok:
      return None
    if tok.tag in [Symbol.STRING, Symbol.NUMBER, Symbol.SYMBOL]:
      return tok
    if tok.tag == Symbol.LPAREN:
      return self.readlist()
    if tok.tag == Symbol.RPAREN:
      raise ParserException, "unexpected RPAREN"
  def readlist(self):
    l = []
    while True:
      tok = self.lexer.token()
      if not tok:
        raise ParserException, "unexpected EOF"
      if tok.tag == Symbol.RPAREN:
        return l
      if tok.tag == Symbol.LPAREN:
        l.append(self.readlist())
      else:
        l.append(tok)

class KuaoException(Exception):
  pass

class Env:
  def __init__(self, parent=None):
    self.parent = parent
    self.bindings = {}
  def lookup(self, key):
    if self.bindings.has_key(key):
      return self.bindings[key]
    elif self.parent:
      return self.parent.lookup(key)
    else:
      raise KuaoException, 'undefined variable: %s' % (key,)
  def add(self, key, value):
    self.bindings[key] = value
  def merge(self, d):
    for k in d.keys():
      self.bindings[k] = d[k]

class Closure:
  def __init__(self, env, args, body):
    self.env = env
    self.args = args
    self.body = body
  def __repr__(self):
    return '#(closure)'

def closurep(exp):
  return isinstance(exp, Closure)

toplevel = Env()

def kuaoeval(env, exp):
  if listp(exp):
    if len(exp) == 0:
      return exp
    else:
      car = kuaoeval(env, exp[0])
      #cdr = map(lambda e: kuaoeval(env, e), exp[1:])
      cdr = exp[1:]
      if callable(car):
        return car(env, cdr)
      elif closurep(car):
        return car.call(cdr)
      else:
        raise KuaoException, "invalid function application"
  elif symbolp(exp):
    return env.lookup(exp.value)
  elif stringp(exp) or numberp(exp):
    return exp.value

def define(env, exp):
  if len(exp) != 2:
    raise KuaoException, "error: define requires 2 arguments"
  bnd = exp[0]
  exp = exp[1]
  if symbolp(bnd):
    e = kuaoeval(env, exp)
    env.add(bnd.value, e)
    return e

def mkclosure(env, exp):
  # form: (lambda (arg1 arg2 ...) body)
  nenv = Env(env)
  pass

def check_list_size(lst, size):
  if not listp(lst):
    raise KuaoException, "error: argument not list"
  if len(lst) < size:
    raise KuaoException, "error: list size must be at least %d" % (size,)

def car(env, exp):
  arg = kuaoeval(env, exp[0])
  check_list_size(arg, 1)
  return arg[0]

def cdr(env, exp):
  arg = kuaoeval(env, exp[0])
  check_list_size(arg, 1)
  return arg[1:]

def quote(env, exp):
  return exp[0]

def mkop1(fn):
  def op(env, exp):
    if len(exp) == 0:
      raise KuaoException, "needs at least 1 arg"
    total = kuaoeval(env, exp[0])
    for e in exp[1:]:
      total = fn(total, kuaoeval(env, e))
    return total
  return op

def mkop(default, fn):
  def op(env, exp):
    total = default
    for e in exp:
      total = fn(total, kuaoeval(env, e))
    return total
  return op

toplevel.merge({
  'define': define,
  'lambda': mkclosure,
  '+': mkop(0, lambda a, b: a+b),
  '-': mkop1(lambda a, b: a-b),
  '*': mkop(1, lambda a, b: a*b),
  '/': mkop1(lambda a, b: a/b),
  'car': car,
  'cdr': cdr,
  'quote': quote
})

def kuaostr(sxp):
  if listp(sxp):
    return "(" + " ".join(map(kuaostr, sxp)) + ")"
  else:
    return str(sxp)

def kuaoprint(sxp):
  print kuaostr(sxp)

def main():
  par = Parser(Lexer())
  while True:
    # Can't use print with ,: it forces leading space next print
    sys.stdout.write('kuao> ')
    sexp = par.read()
    if sexp is None:
      break
    try:
      ret = kuaoeval(toplevel, sexp)
      kuaoprint(ret)
    except KuaoException as e:
      print e

if __name__ == '__main__':
  main()
