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
  def __init__(self, strm):
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
  def find_binding(self, key):
    if self.bindings.has_key(key):
      return self.bindings
    elif self.parent:
      return self.parent.find_binding(key)
    else:
      return None
  def lookup(self, key):
    env = self.find_binding(key)
    if env:
      return env[key]
    else:
      raise KuaoException, 'undefined variable %s' % (key,)
  def update(self, key, value):
    """Sets a previously bound variable to a new value."""
    env = self.find_binding(key)
    if env:
      env[key] = value
    else:
      self.bindings[key] = value
  def define(self, key, value):
    """Adds a new locally bound variable."""
    self.bindings[key] = value
  def merge(self, d):
    for k in d.keys():
      self.bindings[k] = d[k]
  def printe(self, indent=0):
    ind = ' ' * indent
    print "%s{" % (ind,)
    for k, v in self.bindings.items():
      print "%s%s=%s" % (ind, str(k), str(v))
    print "%s{" % (ind,)
    if self.parent:
      self.parent.printe(indent+2)

class Closure:
  def __init__(self, env, params, body):
    self.env = env
    self.params = params
    self.body = body
  def call(self, args):
    if len(args) != len(self.params):
      raise KuaoException, "error: expected %d arguments, got %d" % (len(self.params), len(args))
    for k, v in zip(self.params, map(lambda e: kuaoeval(self.env, e), args)):
      self.env.define(k.value, v)
    #self.env.printe()
    ret = None
    for form in self.body:
      ret = kuaoeval(self.env, form)
    return ret
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
  if not symbolp(bnd):
    raise KuaoException, "error: arg #1 must be symbol"
  e = kuaoeval(env, exp)
  env.define(bnd.value, e)

def setf(env, exp):
  if len(exp) != 2:
    raise KuaoException, "error: set! requires 2 arguments"
  bnd = exp[0]
  exp = exp[1]
  if not symbolp(bnd):
    raise KuaoException, "error: arg #1 must be symbol"
  e = kuaoeval(env, exp)
  env.update(bnd.value, e)

def mkclosure(env, exp):
  # form: (lambda (arg1 arg2 ...) body)
  nenv = Env(env)
  args = exp[0]
  if not all(map(symbolp, args)):
    raise KuaoException, "error: non-symbol in arglist"
  closure = Closure(nenv, args, exp[1:])
  return closure

def mklist(env, exp):
  return map(lambda e: kuaoeval(env, e), exp)

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
      ee = kuaoeval(env, e)
      total = fn(total, ee)
    return total
  return op

def display(env, exp):
  for e in exp:
    ee = kuaoeval(env, e)
    if ee is None:
      sys.stdout.write("#(undef)")
    else:
      sys.stdout.write(str(ee))

toplevel.merge({
  'define': define,
  'set!': setf,
  'lambda': mkclosure,
  '+': mkop(0, lambda a, b: a+b),
  '-': mkop1(lambda a, b: a-b),
  '*': mkop(1, lambda a, b: a*b),
  '/': mkop1(lambda a, b: a/b),
  'car': car,
  'cdr': cdr,
  'quote': quote,
  'list': mklist,
  'display': display
})

def kuaostr(sxp):
  if listp(sxp):
    return "(" + " ".join(map(kuaostr, sxp)) + ")"
  else:
    return str(sxp)

def kuaoprint(sxp):
  print kuaostr(sxp)

def repl(p, interactive=True):
  while True:
    # Can't use print with ,: it forces leading space next print
    if interactive:
      sys.stdout.write('kuao> ')
    sexp = p.read()
    if sexp is None:
      break
    try:
      ret = kuaoeval(toplevel, sexp)
      if ret is not None and interactive:
        kuaoprint(ret)
    except KuaoException as e:
      if interactive:
        print e
      else:
        raise e

def main():
  strm = open(sys.argv[1]) if len(sys.argv) > 1 else sys.stdin
  lexer = Lexer(strm)
  parser = Parser(lexer)
  repl(parser, strm is sys.stdin)

if __name__ == '__main__':
  main()
