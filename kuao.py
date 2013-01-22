#!/usr/bin/python

import sys
import string

class String:
  def __init__(self, value):
    self.value = value
  def __str__(self):
    return '"' + self.value + '"'
  def eval(self, env):
    return self

class Number:
  def __init__(self, value):
    self.value = value
  def __eq__(self, other):
   return isinstance(other, self.__class__) and self.value == other.value
  def __ne__(self, other):
    return not self.__eq__(other)
  def __str__(self):
    return str(self.value)
  def eval(self, env):
    return self

class Symbol:
  def __init__(self, value):
    self.value = value
  def __hash__(self):
    return hash(self.value)
  def __eq__(self, other):
   return isinstance(other, self.__class__) and self.value == other.value
  def __ne__(self, other):
    return not self.__eq__(other)
  def __str__(self):
    return self.value
  def eval(self, env):
    return env.lookup(self)

class Boolean:
  def __init__(self, value):
    self.value = value
  def __str__(self):
    if self.value:
      return '#t'
    else:
      return '#f'
  def eval(self, env):
    return self

T = Boolean(True)
F = Boolean(False)

class NullType:
  def __init__(self):
    pass
  def __str__(self):
    return '()'
  def each(self):
    return []
  def length(self):
    return 0
  def evlist(self, env):
    return self
  def eval(self, env):
    return self

Null = NullType()

class UndefinedType:
  def __init__(self):
    pass
  def __str__(self):
    return '#(undef)'

Undef = UndefinedType()

class Pair:
  def __init__(self, car, cdr):
    self.car, self.cdr = car, cdr
  def evlist(self, env):
    ecar = self.car.eval(env)
    if isinstance(self.cdr, Pair):
      return Pair(ecar, self.cdr.evlist(env))
    else:
      return Pair(ecar, self.cdr.eval(env))
  def eval(self, env):
    car = self.car.eval(env)
    if isinstance(car, Special):
      # Don't eval args for special forms
      cdr = self.cdr
      return car(env, cdr)
    elif callable(car):
      cdr = self.cdr.evlist(env)
      return car(env, cdr)
    else:
      raise KuaoException, 'illegal function invocation'
  def length(self):
    length = 0
    for x in self.each():
      length += 1
    return length
  def each(self):
    car = self.car
    cdr = self.cdr
    yield car
    while cdr is not Null:
      car = cdr.car
      cdr = cdr.cdr
      yield car
  def __str__(self):
    def insides(car, cdr):
      if isinstance(cdr, Pair):
        return str(car) + ' ' + insides(cdr.car, cdr.cdr)
      elif cdr is Null:
        return str(car)
      else:
        return str(car) + ' . ' + str(cdr)
    return '(' + insides(self.car, self.cdr) + ')'

class Special:
  def __init__(self, fn):
    self.fn = fn
  def __str__(self):
    return '#(special)'
  def __call__(self, env, args):
    return self.fn(env, args)

class Primitive:
  def __init__(self, fn):
    self.fn = fn
  def __str__(self):
    return '#(primitive)'
  def __call__(self, env, args):
    return self.fn(env, args)

class Closure:
  def __init__(self, env, params, body):
    self.env = env
    self.params = params
    self.body = body
  def __str__(self):
    return '#(closure)'
  def __call__(self, env, args):
    nenv = Env(self.env)
    # variable arg lambda
    if isinstance(self.params, Symbol):
      nenv.define(self.params, args)
    ret = Undef
    for form in self.body.each():
      ret = form.eval(nenv)
    return ret

def pairp(e):
  return isinstance(e, List)

def symbolp(e):
  return isinstance(e, Symbol)

def stringp(e):
  return isinstance(e, String)

def numberp(e):
  return isinstance(e, Number)

def booleanp(e):
  return isinstance(e, Boolean)

class Reader:
  def __init__(self, strm):
    self.stream = strm
    self.ch = None
  def peek(self):
    if self.ch is None:
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
    self.buf = []
  def get(self):
    if self.buf:
      fst, rest = self.buf[0], self.buf[1:]
      self.buf = rest
      return fst
    else:
      return self.token()
  def unget(self, t):
    self.buf.append(t)
  def token(self):
    r = self.rdr
    c = r.peek()
    if not c:
      return None
    elif c == '(' or c == ')':
      r.nxt()
      return c 
    elif c == '\'':
      r.nxt()
      return c
    elif c == '.':
      r.nxt()
      return c
    elif c == '"':
      r.nxt()
      return String(self.readstr())
    elif c == '#':
      r.nxt()
      return Boolean(self.readbool())
    elif c in string.digits:
      return Number(self.readnum())
    elif c in string.ascii_letters or c in '!?%*+-.:<=>^_~/\\':
      return Symbol(self.readsym())
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
  def readbool(self):
    r = self.rdr
    c = r.peek()
    if c == 't':
      r.nxt()
      return True
    elif c == 'f':
      r.nxt()
      return False
    else:
      raise LexerException, 'boolean must be #t or #f'

class ParserException(Exception):
  pass

class Parser:
  def __init__(self, lex):
    self.lexer = lex
  def error(self, s):
    raise ParserException, s
  def atomp(self, t):
    return self.oneof(t, [String, Boolean, Symbol, Number])
  def oneof(self, tok, ts):
    return any(map(lambda t: isinstance(tok, t), ts))
  def sexp(self):
    # sexp : STRING
    #      | BOOLEAN
    #      | SYMBOL
    #      | NUMBER
    #      | pair
    #      | '\'' sexp
    t = self.lexer.get()
    if t is None:
      return t
    if self.atomp(t):
      return t
    elif t == '(':
      return self.pair()
    elif t == '\'':
      s = self.sexp()
      return Pair(Symbol('quote'), Pair(s, Null))
    else:
      self.error("unexpected token '%s'" % t)
  def pair(self):
    # pair : '(' sexp* ')'
    #      | '(' sexp+ . sexp ')'
    t = self.lexer.get()
    if t == ')':
      return Null
    elif t == '\'':
      self.lexer.unget(t)
      s = self.sexp()
      return Pair(s, self.pair())
    elif self.atomp(t):
      return Pair(t, self.pair())
    elif t == '.':
      s = self.sexp()
      t = self.lexer.get()
      if t != ')':
        self.error("expected token ')', got '%s'" % t)
      return s
    else:
      fst = self.pair()
      snd = self.pair()
      return Pair(fst, snd)

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
    return self
  def printe(self, indent=0):
    ind = ' ' * indent
    print "%s{" % (ind,)
    for k, v in self.bindings.items():
      print "%s%s=%s" % (ind, str(k), str(v))
    print "%s}" % (ind,)
    if self.parent:
      self.parent.printe(indent+2)

def error(s):
  raise KuaoException, s

def define(env, exp):
  sym = exp.car
  val = exp.cdr.car
  if not symbolp(sym):
    raise KuaoException, "error: arg #1 must be symbol"
  e = val.eval(env)
  env.define(sym, e)
  return Undef

def setf(env, exp):
  sym = exp.car
  val = exp.cdr.car
  if not symbolp(sym):
    error("error: arg #1 must be symbol")
  e = val.eval(env)
  env.update(sym, e)
  return Undef

def display(env, exp):
  val = exp.car
  sys.stdout.write(val.value if isinstance(val, String) else str(val))
  return Undef

def quote(env, exp):
  if exp is Null or exp.cdr is not Null:
    error("'quote' requires 1 arg")
  return exp.car

def runif(env, exp):
  if exp.length() < 2:
    error("'if' requires 2 or 3 arguments")
  cond = exp.car
  true = exp.cdr.car
  false = exp.cdr.cdr
  e = cond.eval(env)
  if isinstance(e, Boolean) and e.value:
    return true.eval(env)
  elif isinstance(e, Boolean) and not e.value:
    if false is Null:
      return Undef
    else:
      return false.car.eval(env)
  else:
    return true.eval(env)

def checktype(scope, exp, typ):
  if not isinstance(exp, typ):
    error("argument to '%s' must be of type '%s'" % (scope, typ))

def numeq(env, exp):
  if exp.length() < 2:
    error("'=' requires at least 2 arguments")
  fst = exp.car
  checktype('=', fst, Number)
  snd = exp.cdr.car
  checktype('=', snd, Number)
  if fst != snd:
    return F
  else:
    es = exp.cdr.cdr
    for num in es.each():
      if num != fst:
        return F
    return T

def plus(env, exp):
  n = Number(0)
  for m in exp.each():
    n = Number(n.value + m.value)
  return n

def multiply(env, exp):
  n = Number(1)
  for m in exp.each():
    n = Number(n.value * m.value)
  return n

def subtract(env, exp):
  if exp is Null:
    error("'-' requires at least 1 argument")
  n = exp.car
  if exp.cdr is Null:
    return Number(n.value * -1)
  for m in exp.cdr.each():
    n = Number(n.value - m.value)
  return n

def mklambda(env, exp):
  if exp is Null or exp.cdr is Null:
    error("lambda requires 2 arguments")
  args = exp.car
  body = exp.cdr.car
  return Closure(env, args, body)

toplevel = Env().merge({
  Symbol('define') : Special(define),
  Symbol('set!')   : Special(setf),
  Symbol('if')     : Special(runif),
  Symbol('display'): Primitive(display),
  Symbol('=')      : Primitive(numeq),
  Symbol('+')      : Primitive(plus),
  Symbol('*')      : Primitive(multiply),
  Symbol('-')      : Primitive(subtract),
  Symbol('lambda') : Special(mklambda),
  Symbol('quote')  : Special(quote)
})

def repl(p, interactive=True):
  while True:
    # Can't use print with ,: it forces leading space next print
    if interactive:
      sys.stdout.write('kuao> ')
    sexp = p.sexp()
    if sexp is None:
      break
    try:
      ret = sexp.eval(toplevel)
      if ret not in [None, Undef] and interactive:
        print ret
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
