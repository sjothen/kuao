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
  def __str__(self):
    return str(self.value)
  def eval(self, env):
    return self

class Symbol:
  def __init__(self, value):
    self.value = value
  def __str__(self):
    return self.value
  def eval(self, env):
    return env.lookup(self.value)

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

class List:
  def __init__(self, value):
    self.value = value
  def car(self):
    return self.value[0]
  def cdr(self):
    return self.value[1:]
  def __str__(self):
    return "(" + " ".join(map(str, self.value)) + ")"

class NullType:
  def __init__(self):
    pass
  def __str__(self):
    return '()'
  def eval(self):
    return self

Null = NullType()

class Pair:
  def __init__(self, car, cdr):
    self.car, self.cdr = car, cdr
  def __str__(self):
    def insides(car, cdr):
      if isinstance(cdr, Pair):
        return str(car) + ' ' + insides(cdr.car, cdr.cdr)
      elif cdr is Null:
        return str(car)
      else:
        return str(car) + ' . ' + str(cdr)
    return '(' + insides(self.car, self.cdr) + ')'

#print Pair(Number(1), Pair(Pair(Number(1), Null), Pair(Number(2), Number(3))))
#print Pair(Number(1), Number(2))

def listp(e):
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
  def printe(self, indent=0):
    ind = ' ' * indent
    print "%s{" % (ind,)
    for k, v in self.bindings.items():
      print "%s%s=%s" % (ind, str(k), str(v))
    print "%s}" % (ind,)
    if self.parent:
      self.parent.printe(indent+2)

class Builtin:
  def __init__(self, fn):
    self.function = fn
  def eval(self, args):
    pass

class Closure:
  def __init__(self, env, params, body):
    self.env = env
    self.params = params
    self.body = body
  def call(self, env, args):
    if len(args) != len(self.params):
      raise KuaoException, "error: expected %d arguments, got %d" % (len(self.params), len(args))
    # evaluate arguments in callers env!
    eargs = map(lambda e: kuaoeval(env, e), args)
    # new env has closed env as parent
    nenv = Env(self.env)
    for k, v in zip(self.params, eargs):
      # add args to new env
      nenv.define(k.value, v)
    ret = None
    for form in self.body:
      ret = kuaoeval(nenv, form)
    return ret
  def __repr__(self):
    return '#(closure)'

def closurep(exp):
  return isinstance(exp, Closure)

toplevel = Env()

def kuaoeval(env, exp):
  if listp(exp):
    if len(exp.value) == 0:
      return exp
    else:
      car = kuaoeval(env, exp.value[0])
      cdr = exp.value[1:]
      print car, cdr
      if callable(car):
        return car(env, cdr)
      elif closurep(car):
        return car.call(env, cdr)
      else:
        raise KuaoException, "invalid function application"
  elif symbolp(exp):
    return env.lookup(exp.value)
  elif stringp(exp) or numberp(exp) or booleanp(exp):
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
    print exp
    es = map(lambda e: kuaoeval(env, e), exp)
    print es
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

def check1eval(env, exp):
  if len(exp) != 1:
    raise KuaoException, "error: requires 1 argument"
  e = kuaoeval(env, exp[0])
  return e

def symbolq(env, exp):
  e = check1eval(env, exp)
  return isinstance(e, Symbol) and symbolp(e)

def stringq(env, exp):
  e = check1eval(env, exp)
  return isinstance(e, str)

def numberq(env, exp):
  e = check1eval(env, exp)
  return isinstance(e, int)

def listq(env, exp):
  e = check1eval(env, exp)
  return isinstance(e, list)

def booleanq(env, exp):
  e = check1eval(env, exp)
  return isinstance(e, bool)

def doif(env, exp):
  # (if cond texp fexp)
  if len(exp) not in [2, 3]:
    raise KuaoException, "error: if requires 2 or 3 args"
  cond = kuaoeval(env, exp[0])
  if isinstance(cond, bool) and not cond:
    if len(exp) == 3:
      return kuaoeval(env, exp[2])
    else:
      return None
  else:
    return kuaoeval(env, exp[1])

def numeq(env, exp):
  if len(exp) < 2:
    raise KuaoException, "error: requires at least 2 args"
  ns = map(lambda e: kuaoeval(env, e), exp)
  if not all(map(lambda n: isinstance(n, int), ns)):
    raise KuaoException, "error: all args must be numbers"
  first = ns[0]
  return all(map(lambda n: n == first, ns))

def nullp(env, exp):
  if len(exp) != 1:
    raise KuaoException, "error: requires 1 arg"
  arg = kuaoeval(env, exp[0])
  if isinstance(arg, list):
    return len(arg) == 0
  else:
    return False

def compare(fn):
  def wrapped(env, exp):
    if len(exp) < 2:
      raise KuaoException, "error: requires at least 2 args"
    args = map(lambda e: kuaoeval(env, e), exp)
    for i in range(0,len(args)-1):
      if not fn(args[i], args[i+1]):
        return False
    return True
  return wrapped

toplevel.merge({
  'define': define,
  'if': doif,
  'set!': setf,
  'lambda': mkclosure,
  '=': compare(lambda a, b: a == b),
  '<=': compare(lambda a, b: a <= b),
  '<': compare(lambda a, b: a < b),
  '>=': compare(lambda a, b: a >= b),
  '>': compare(lambda a, b: a > b),
  '+': mkop(0, lambda a, b: a+b),
  '-': mkop1(lambda a, b: a-b),
  '*': mkop(1, lambda a, b: a*b),
  '/': mkop1(lambda a, b: a/b),
  'car': car,
  'cdr': cdr,
  'quote': quote,
  'list': mklist,
  'display': display,
  'symbol?': symbolq,
  'string?': stringq,
  'number?': numberq,
  'list?': listq,
  'boolean?': booleanq,
  'null?': nullp
})

def kuaostr(sxp):
  if listp(sxp):
    return "(" + " ".join(map(kuaostr, sxp)) + ")"
  elif isinstance(sxp, bool):
    if sxp:
      return '#t'
    else:
      return '#f'
  elif callable(sxp):
    return '#(closure %s)' % sxp.__name__
  else:
    return str(sxp)

def kuaoprint(sxp):
  print kuaostr(sxp)

def repl(p, interactive=True):
  while True:
    # Can't use print with ,: it forces leading space next print
    if interactive:
      sys.stdout.write('kuao> ')
    sexp = p.sexp()
    if sexp is None:
      break
    print sexp
    #try:
      #ret = kuaoeval(toplevel, sexp)
      #if ret is not None and interactive:
      #  kuaoprint(ret)
    #except KuaoException as e:
    #  if interactive:
    #    print e
    #  else:
    #    raise e

def main():
  strm = open(sys.argv[1]) if len(sys.argv) > 1 else sys.stdin
  lexer = Lexer(strm)
  parser = Parser(lexer)
  repl(parser, strm is sys.stdin)

if __name__ == '__main__':
  main()
