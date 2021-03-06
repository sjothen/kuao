#!/usr/bin/python

import os
import sys
import string
import itertools as it

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
    #error("illegal empty application")

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
    self.proper = cdr is Null or (isinstance(cdr, Pair) and cdr.proper)
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
    while cdr is not Null and isinstance(cdr, Pair):
      car = cdr.car
      cdr = cdr.cdr
      yield car
  def __str__(self):
    spec = {
        'unquote': ',',
        'quasiquote': '`',
        'quote': '\'',
        'unquote-splicing': ',@'
    }
    def isspecial(sym):
      if not isinstance(sym, Symbol):
        return False
      v = sym.value
      return v == 'unquote' or v == 'quasiquote' or v == 'quote' or v == 'unquote-splicing'
    def insides(car, cdr):
      rep = ''
      while True:
        if isinstance(cdr, Pair):
          if isspecial(car):
            rep += spec[car.value]
          else:
            rep += str(car) + ' '
          car = cdr.car
          cdr = cdr.cdr
        elif cdr is Null:
          rep += str(car)
          break
        else:
          rep += str(car) + ' . ' + str(cdr)
          break
      return rep
    if isspecial(self.car):
      return insides(self.car, self.cdr)
    else:
      return '(' + insides(self.car, self.cdr) + ')'

def checkproper(xs):
  if xs is not Null and not xs.proper:
    error("application with improper list not allowed")

class Special:
  def __init__(self, fn, name):
    self.fn = fn
    self.name = name
  def __str__(self):
    return '#(syntax %s)' % self.name
  def __call__(self, env, args):
    checkproper(args)
    return self.fn(env, args)

class Primitive:
  def __init__(self, fn, name):
    self.fn = fn
    self.name = name
  def __str__(self):
    return '#(primitive %s)' % self.name
  def __call__(self, env, args):
    checkproper(args)
    return self.fn(env, args)

class Recurse:
  def __init__(self, func, *args):
    self.func = func
    self.args = args
  def __call__(self):
    return self.func(*self.args)

class Closure:
  def __init__(self, env, params, body):
    self.env = env
    self.params = params
    self.body = body
    self.name = None
  def __str__(self):
    if not self.name:
      return '#(lambda)'
    else:
      return '#(function %s)' % self.name

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
    elif c == '`':
      r.nxt()
      return c
    elif c == ',':
      r.nxt()
      if r.peek() == '@':
        r.nxt()
        return ',@'
      return c
    elif c == ';':
      self.skipcomment()
      return self.token()
    elif c == '.':
      r.nxt()
      return c
    elif c == '"':
      r.nxt()
      return String(self.readstr())
    elif c == '#':
      r.nxt()
      return self.readbool()
    elif c in string.digits:
      return Number(self.readnum())
    elif c in string.ascii_letters or c in '+-*/<=>!?:$%_&~^':
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
  def skipcomment(self):
    r = self.rdr
    while r.peek() and r.peek() != '\n':
      r.nxt()
    r.nxt()
  def skipws(self):
    r = self.rdr
    while r.peek() and r.peek() in string.whitespace:
      r.nxt()
  def readstr(self):
    esc = {
      '\\': '\\',
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
          raise LexerException, "unknown escape code '%s' in string" % (r.peek(),)
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
    c = string.ascii_letters + string.digits + '+-*/<=>!?:$%_&~^'
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
      return T
    elif c == 'f':
      r.nxt()
      return F
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
      return self.pair(True)
    elif t == '\'':
      s = self.sexp()
      return Pair(Symbol('quote'), Pair(s, Null))
    elif t == '`':
      s = self.sexp()
      return Pair(Symbol('quasiquote'), Pair(s, Null))
    elif t == ',':
      s = self.sexp()
      return Pair(Symbol('unquote'), Pair(s, Null))
    elif t == ',@':
      s = self.sexp()
      return Pair(Symbol('unquote-splicing'), Pair(s, Null))
    else:
      self.error("unexpected token '%s'" % t)
  def pair(self, first=False):
    # pair : '(' sexp* ')'
    #      | '(' sexp+ . sexp ')'
    t = self.lexer.get()
    if t == ')':
      return Null
    elif t == '\'' or t == '`' or t == ',' or t == ',@':
      self.lexer.unget(t)
      s = self.sexp()
      return Pair(s, self.pair())
    elif self.atomp(t):
      return Pair(t, self.pair())
    elif t == '.':
      if first:
        self.error("expected sexp before '.'")
      s = self.sexp()
      t = self.lexer.get()
      if t != ')':
        self.error("expected token ')', got '%s'" % t)
      return s
    else:
      fst = self.pair(True)
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
  raise KuaoException, 'error: %s' % s

def check(name, exp, nargs):
  length = exp.length()
  if length != nargs:
    error("'%s' requires %d args, got %d" % (name, nargs, length))

def checktype(scope, exp, typ):
  if not isinstance(exp, typ):
    error("argument to '%s' must be of type '%s'" % (scope, typ))

toplevel = Env()

def special(name):
  def wrapper(fn, name=name):
    global toplevel
    toplevel.define(Symbol(name), Special(fn, name))
    return fn
  return wrapper

def primitive(name):
  def wrapper(fn, name=name):
    global toplevel
    toplevel.define(Symbol(name), Primitive(fn, name))
    return fn
  return wrapper

class Macro:
  def __init__(self, name, params, body, env):
    self.name = name
    self.params = params
    self.body = body
    self.env = env
  def __str__(self):
    return "#(macro %s)" % self.name

# (define-macro (when cond . body)
#   `(if ,cond
#      (begin
#        ,@body)))
#

@special('define-macro')
def definemacro(env, exp):
  sym = exp.car
  if not isinstance(sym, Pair):
    error("error: arg #1 of define-macro must be a list")
  if exp.cdr is Null:
    error("error: define-macro requires 2 arguments")
  body = exp.cdr.car
  mac = Macro(sym.car, sym.cdr, body, env)
  env.define(sym.car, mac)
  return Undef

@special('define')
def define(env, exp):
  sym = exp.car
  val = exp.cdr.car
  if isinstance(sym, Pair):
    name = sym.car
    args = sym.cdr
    body = exp.cdr
    closure = keval(env, Pair(Symbol('lambda'), Pair(args, body)))
    closure.name = name
    env.define(name, closure)
  elif isinstance(sym, Symbol):
    # Force eval thru tramp, dont want to be lazy
    e = keval(env, val)
    e = tramp(e)
    env.define(sym, e)
  else:
    error("error: arg #1 must be symbol or list")
  return Undef

@special('set!')
def setf(env, exp):
  sym = exp.car
  val = exp.cdr.car
  if not symbolp(sym):
    error("error: arg #1 must be symbol")
  # Force eval
  e = tramp(keval(env, val))
  env.update(sym, e)
  return Undef

@special('let')
def let(env, exp):
  length = exp.length()
  if length < 2:
    error("'let' syntax requires at least 2 arguments, given %d" % length)
  tups = exp.car
  body = exp.cdr
  if not isinstance(tups, Pair) or not tups.proper:
    if tups is not Null:
      error("1st argument of 'let' isn't a proper list")
  def getfn(tuples, fn):
    if tuples is Null:
      return Null
    else:
      pararg = tuples.car
      if not isinstance(pararg, Pair) or pararg.length() != 2 or not pararg.proper:
        error("key-value pair in 'let' must be proper list of length 2")
      return Pair(fn(pararg), getfn(tuples.cdr, fn))
  pars = getfn(tups, lambda t: t.car)
  args = getfn(tups, lambda t: t.cdr.car)
  p = Pair(Pair(Symbol('lambda'), Pair(pars, body)), args)
  return p.eval(env)

@special('quote')
def quote(env, exp):
  if exp is Null or exp.cdr is not Null:
    error("'quote' requires 1 arg")
  return exp.car

class Spliced:
  def __init__(self, p):
    self.pair = p

def addtoend(v, ps):
  if v is Null:
    return ps
  else:
    return Pair(v.car, addtoend(v.cdr, ps))

def quasiquoter(env, p, depth=1):
  if isinstance(p, Pair):
    car = p.car
    cdr = p.cdr
    if isinstance(car, Symbol):
      if car.value == 'unquote':
        if depth - 1 == 0:
          e = keval(env, cdr.car)
          e = tramp(e)
          return e
        else:
          return Pair(Symbol('unquote'), Pair(quasiquoter(env, cdr.car, depth-1), Null))
      elif car.value == 'unquote-splicing':
        if depth - 1 == 0:
          e = keval(env, cdr.car)
          e = tramp(e)
          return Spliced(e)
        else:
          return Pair(Symbol('unquote-splicing'), Pair(quasiquoter(env, cdr.car, depth-1), Null))
      elif car.value == 'quasiquote':
        return Pair(Symbol('quasiquote'), Pair(quasiquoter(env, cdr.car, depth+1), Null))
        #return p
    ncar = quasiquoter(env, p.car, depth)
    ncdr = quasiquoter(env, p.cdr, depth)
    if isinstance(ncar, Spliced):
      return addtoend(ncar.pair, ncdr)
    else:
      return Pair(ncar, ncdr)
  elif isinstance(p, Symbol):
    return p
  elif numberp(p) or booleanp(p) or stringp(p):
    return p
  elif p is Null:
    return Null

@special('quasiquote')
def quasiquote(env, exp):
  if exp is Null or exp.cdr is not Null:
    error("'quasiquote' requires 1 arg")
  return quasiquoter(env, exp.car)

@special('if')
def runif(env, exp):
  if exp.length() < 2:
    error("'if' requires 2 or 3 arguments")
  cond = exp.car
  true = exp.cdr.car
  false = exp.cdr.cdr
  e = tramp(keval(env, cond))
  if isinstance(e, Boolean) and e.value:
    return tramp(keval(env, true))
  elif isinstance(e, Boolean) and not e.value:
    if false is Null:
      return Undef
    else:
      return tramp(keval(env, false.car))
  else:
    return tramp(keval(env, true))

@special('lambda')
def mklambda(env, exp):
  if exp is Null or exp.cdr is Null:
    error("lambda requires 2 arguments")
  args = exp.car
  body = Pair(Symbol('begin'), exp.cdr)
  return Closure(env, args, body)

@special('begin')
def begin(env, exp):
  ret = Undef
  for form in exp.each():
    ret = keval(env, form)
    ret = tramp(ret)
  return ret

@special('and')
def kand(env, exp):
  ret = T
  for e in exp.each():
    ev = e.eval(env)
    if ev is F:
      return F
    ret = ev
  return ret

@special('or')
def kor(env, exp):
  ret = F
  for e in exp.each():
    ev = e.eval(env)
    if ev is not F:
      return ev
    ret = ev
  return ret

@primitive('display')
def display(env, exp):
  val = exp.car
  pr = val.value if isinstance(val, String) else str(val)
  sys.stdout.write(pr)
  return Undef

@primitive('+')
def plus(env, exp):
  n = Number(0)
  for m in exp.each():
    n = Number(n.value + m.value)
  return n

@primitive('*')
def multiply(env, exp):
  n = Number(1)
  for m in exp.each():
    n = Number(n.value * m.value)
  return n

@primitive('-')
def subtract(env, exp):
  if exp is Null:
    error("'-' requires at least 1 argument")
  n = exp.car
  if exp.cdr is Null:
    return Number(n.value * -1)
  for m in exp.cdr.each():
    n = Number(n.value - m.value)
  return n

@primitive('car')
def car(env, exp):
  if exp is Null:
    error("'car' requires 1 argument")
  if not isinstance(exp.car, Pair):
    error('cannot take car of non-pair')
  return exp.car.car

@primitive('cdr')
def cdr(env, exp):
  if exp is Null:
    error("'cdr' requires 1 argument")
  if exp.car is Null or not isinstance(exp.car, Pair):
    error('cannot take cdr of non-pair')
  return exp.car.cdr

@primitive('cons')
def cons(env, exp):
  arglen = exp.length()
  if arglen != 2:
    error("'cons' requires 2 arguments, given %d" % arglen)
  a = exp.car
  b = exp.cdr.car
  return Pair(a, b)

@primitive('null?')
def nullp(env, exp):
  if exp is Null:
    error("'null?' requires 1 argument")
  return T if exp.car is Null else F

@primitive('not')
def knot(env, exp):
  if exp is Null:
    error("'not' requires 1 argument")
  p = exp.car
  return T if p is F else F

def comp(name, env, exp, comp):
  if exp.length() < 2:
    error("'%s' requires at least 2 arguments" % name)
  fst = exp.car
  checktype(name, fst, Number)
  for n in exp.cdr.each():
    checktype(name, n, Number)
    if not comp(fst.value, n.value):
      return F
    fst = n
  return T

@primitive('<')
def lt(env, exp):
  return comp('<', env, exp, lambda a, b: a < b)

@primitive('>')
def gt(env, exp):
  return comp('>', env, exp, lambda a, b: a > b)

@primitive('<=')
def lte(env, exp):
  return comp('<=', env, exp, lambda a, b: a <= b)

@primitive('>=')
def gte(env, exp):
  return comp('>=', env, exp, lambda a, b: a >= b)

@primitive('=')
def numeq(env, exp):
  return comp('=', env, exp, lambda a, b: a == b)

@primitive('apply')
def kapply(env, exp):
  length = exp.length()
  if length != 2:
    error("'apply' requires 2 arguments, given %d" % length)
  fn = exp.car
  lst = exp.cdr.car
  return fn(env, lst)

@primitive('pair?')
def pairp(env, exp):
  check('pair?', exp, 1)
  arg = exp.car
  return T if isinstance(arg, Pair) else F

@primitive('list?')
def listp(env, exp):
  check('list?', exp, 1)
  arg = exp.car
  return T if (isinstance(arg, Pair) and arg.proper) or arg is Null else F

@primitive('eqv?')
def eqvp(env, exp):
  check('eqv?', exp, 2)
  arg1 = exp.car
  arg2 = exp.cdr.car
  if arg1.__class__ != arg2.__class__:
    return F
  else:
    if isinstance(arg1, Symbol) or isinstance(arg1, Number):
      return T if arg1 == arg2 else F
    elif arg1 is Null:
      return T
    else:
      return T if arg1 is arg2 else F

def ziptoenv(pars, args, env):
  env.define(pars.car, args.car)
  if isinstance(pars.cdr, Symbol):
    env.define(pars.cdr, args.cdr)
  elif isinstance(pars.cdr, Pair):
    ziptoenv(pars.cdr, args.cdr, env)

def tramp(t):
  while isinstance(t, Recurse):
    t = t()
  return t

def kevalt(env, exp):
  return tramp(keval(env, exp))

def kevalpair(env, exp):
  if exp is Null:
    return Null
  else:
    # Tramp on the eval since argument to fn could be trampoline
    ecar = kevalt(env, exp.car)
    return Pair(ecar, kevalpair(env, exp.cdr))

def macroexpand(env, exp):
  if isinstance(exp.car, Macro):
    return tramp(keval(env, exp))
  else:
    return exp

def mapargstoparams(fun, typ, env, exp):
  """
  Add all arguments to the environment, mapped to their param names. Handles
  the cases where there is a list of formal parameters as well as when there is
  a single symbol.

  This can be used for mapping unevaled forms in macros, or for closures where
  args are eval'd.
  """
  args = kevalpair(env, exp.cdr) if typ == 'closure' else exp.cdr
  nenv = Env(fun.env)
  if isinstance(fun.params, Symbol):
    # (lambda args ...)
    nenv.define(fun.params, args)
  elif isinstance(fun.params, Pair):
    # (lambda (x y ...) ...)
    pl = fun.params.length()
    al = args.length()
    if (fun.params.proper and pl != al) or (not fun.params.proper and al < pl):
      error('%s requires %d%s arguments, given %d' % (typ, pl, '' if fun.params.proper else '+', al))
    ziptoenv(fun.params, args, nenv)
  elif fun.params is not Null:
    error('%s params must be a symbol or list' % typ)
  return nenv

def keval(env, exp):
  if isinstance(exp, (Number, String, Boolean)):
    return exp
  elif isinstance(exp, Symbol):
    return env.lookup(exp)
  elif isinstance(exp, Pair):
    if not exp.proper:
      error('cannot evaluate improper list application')
    fn = tramp(keval(env, exp.car))
    if isinstance(fn, Primitive):
      args = kevalpair(env, exp.cdr)
      return fn(env, args)
    elif isinstance(fn, Special):
      args = exp.cdr
      return fn(env, args)
    elif isinstance(fn, Closure):
      nenv = mapargstoparams(fn, 'closure', env, exp)
      return Recurse(keval, nenv, fn.body)
    elif isinstance(fn, Macro):
      nenv = mapargstoparams(fn, 'macro', env, exp)
      body = fn.body
      if body.car == Symbol('quasiquote'):
        # Expand initial quasiquote form
        body = keval(nenv, fn.body)
      # And then expand the macro
      expanded = macroexpand(env, body)
      # Eval
      return Recurse(keval, env, expanded)
    else:
      error("cannot apply '%s' to '%s'" % (fn, exp.cdr))
  elif isinstance(exp, NullType):
    error('cannot evaluate empty procedure application')

def repl(strm, interactive=True):
  p = Parser(Lexer(strm))
  while True:
    # Can't use print with ,: it forces leading space next print
    if interactive:
      sys.stdout.write('kuao> ')
    try:
      sexp = p.sexp()
      if sexp is None:
        break
      ret = tramp(keval(toplevel, sexp))
      if ret is not Undef and interactive:
        print ret
    except ParserException as e:
      print e
      sys.exit()
    except KuaoException as e:
      if interactive:
        print e
      else:
        raise e

def main():
  strm = open(sys.argv[1]) if len(sys.argv) > 1 else sys.stdin
  # Hack to load the boot file
  boot = os.path.dirname(os.path.abspath(__file__)) + '/boot.ss'
  repl(open(boot), False)
  repl(strm, strm is sys.stdin)

if __name__ == '__main__':
  main()
