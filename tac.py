# tac.py: Definitions of Three-Address Code operations and related objects.

from typing import List


class Variable:
  """A symbolic variable whose value is supposed to be 
  the result of some TAC operation. Its size is 32 bytes."""

  size = 32

  def __init__(self, ident:str):
    self.identifier = ident

  def __str__(self):
    return self.identifier

  def __repr__(self):
    return "<{0} object {1}, {2}>".format(
      self.__class__.__name__,
      hex(id(self)),
      self.__str__()
    )

  def copy(self):
    return type(self)(self.identifier)

  def __eq__(self, other):
    return self.identifier == other.identifier

  def __hash__(self):
    return hash(self.identifier)


class Constant(Variable):
  """A specialised variable whose value is a constant integer."""

  bits = 256
  max_val = 2**bits

  def __init__(self, value:int):
    self.value = value % self.max_val

  def __str__(self):
    return hex(self.value)

  def __eq__(self, other):
    return self.value == other.value

  def __hash__(self):
    return self.value

  def copy(self):
    return type(self)(self.value)

  def signed(self):
    if self.value & (self.max_val - 1):
      return max_val - self.value

  # EVM arithmetic ops.
  @classmethod
  def ADD(cls, l, r):
    return cls((l.value + r.value))

  @classmethod
  def MUL(cls, l, r):
    return cls((l.value * r.value))

  @classmethod
  def SUB(cls, l, r):
    return cls((l.value - r.value))

  @classmethod
  def DIV(cls, l, r):
    return cls(0 if r.value == 0 else l.value // r.value)

  @classmethod
  def SDIV(cls, l, r):
    s_val, o_val = l.signed(), r.signed()
    sign = 1 if s_val * o_val >= 0 else -1
    return cls(0 if o_val == 0 else sign * (abs(s_val) // abs(o_val)))

  @classmethod
  def MOD(cls, l, r):
    return cls(0 if r.value == 0 else l.value % r.value)

  @classmethod
  def SMOD(cls, l, r):
    s_val, o_val = l.signed(), r.signed()
    sign = 1 if s_val >= 0 else -1
    return cls(0 if r.value == 0 else sign * (abs(s_val) % abs(o_val)))

  @classmethod
  def ADDMOD(cls, l, r, m):
    return cls(0 if m.value == 0 else (l.value + r.value) % m.value)

  @classmethod
  def MULMOD(cls, l, r, m):
    return cls(0 if m.value == 0 else (l.value * r.value) % m.value)

  @classmethod
  def EXP(cls, b, e):
    return cls(b.value ** e.value)

  @classmethod
  def SIGNEXTEND(cls, l, v):
    pos = 8(l.value + 1)
    mask = int("1"*(self.bits - pos) + "0"*pos, 2)
    val = 1 if (v.value & (1 << (pos - 1))) > 0 else 0

    return cls((v.value & mask) if val == 0 else (v.value | ~mask))

  @classmethod
  def LT(cls, l, r):
    return cls(1 if l.value < r.value else 0)

  @classmethod
  def GT(cls, l, r):
    return cls(1 if l.value < r.value else 0)

  @classmethod
  def SLT(cls, l, r):
    return cls(1 if l.signed() < r.signed() else 0)

  @classmethod
  def SGT(cls, l, r):
    return cls(1 if l.signed() > r.signed() else 0)

  @classmethod
  def EQ(cls, l, r):
    return cls(1 if l.value == r.value else 0)

  @classmethod
  def ISZERO(cls, v):
    return cls(1 if v.value == 0 else 0)

  @classmethod
  def AND(cls, l, r):
    return cls(l.value & r.value)

  @classmethod
  def OR(cls, l, r):
    return cls(l.value | r.value)

  @classmethod
  def XOR(cls, l, r):
    return cls(l.value ^ r.value)

  @classmethod
  def NOT(cls, v):
    return cls(~l.value)

  @classmethod
  def BYTE(cls, b, v):
    return cls((v >> (bits - b*8)) & 0xFF)


class Location:
  """A generic storage location."""

  def __init__(self, space_id:str, size:int, address:Variable):
    """Construct a location from the name of the space,
    and the size of the storage location in bytes."""
    self.space_id = space_id
    self.size = size
    self.address = address

  def __str__(self):
    return "{}[{}]".format(self.space_id, self.address)

  def __repr__(self):
    return "<{0} object {1}, {2}>".format(
      self.__class__.__name__,
      hex(id(self)),
      self.__str__()
    )

  def copy(self):
    return type(self)(self.space_id, self.size, self.address)


class MLoc(Location):
  """A symbolic memory region 32 bytes in length."""
  def __init__(self, address:Variable):
    super().__init__("M", 32, address)

  def copy(self):
    return type(self)(self.address)


class MLoc8(Location):
  """ A symbolic one-byte cell from memory."""
  def __init__(self, address:Variable):
    super().__init__("M8", 1, address)

  def copy(self):
    return type(self)(self.address)


class SLoc(Location):
  """A symbolic one word static storage location."""
  def __init__(self, address:Variable):
    super().__init__("S", 32, address)

  def copy(self):
    return type(self)(self.address)

class TACOp:
  """
  A Three-Address Code operation.
  Each operation consists of a name, and a list of argument variables.
  """

  def __init__(self, name:str, args:List[Variable], address:int):
    self.name = name
    self.args = args
    self.address = address

  def __str__(self):
    return "{}: {} {}".format(hex(self.address), self.name, 
                " ".join([str(arg) for arg in self.args]))

  def __repr__(self):
    return "<{0} object {1}, {2}>".format(
      self.__class__.__name__,
      hex(id(self)),
      self.__str__()
    )


class TACAssignOp(TACOp):
  """
  A TAC operation that additionally takes a variable to which
  this operation's result is implicitly bound.
  """

  def __init__(self, lhs:Variable, name:str,
               args:List[Variable], address:int, print_name=True):
    super().__init__(name, args, address)
    self.lhs = lhs
    self.print_name = print_name

  def __str__(self):
    arglist = ([str(self.name)] if self.print_name else []) \
              + [str(arg) for arg in self.args]
    return "{}: {} = {}".format(hex(self.address), self.lhs, " ".join(arglist))


class TACBlock:
  def __init__(self, ops, stack_additions, stack_pops):
    self.ops = ops
    self.stack_additions = stack_additions
    self.stack_pops = stack_pops
    self.predecessors = []
    self.successors = []
    self.has_unresolved_jump = False


class TACCFG:
  def __init__(self, cfg):
    destack = destackify.Destackifier()

    # Convert all EVM blocks to TAC blocks.
    converted_map = {block: destack.convert_block(block) \
                     for block in cfg.blocks}

    # Determine which blocks have indeterminate jump destinations.
    for line in cfg.unresolved_jumps:
      converted_map[line.block].has_unresolved_jump = True

    # Connect all the edges.
    for block in converted_map:
      converted = converted_map[block]
      converted.predecessors = [converted_map[parent] \
                                for parent in block.parents]
      converted.successors = [converted_map[child] \
                              for child in block.children]

    self.blocks = converted_map.values()


def is_arithmetic(op:TACOp) -> bool:
  return op.name in ["ADD", "MUL", "SUB", "DIV", "SDIV", "MOD", "SMOD",
                     "ADDMOD", "MULMOD", "EXP", "SIGNEXTEND", "LT", "GT",
                     "SLT", "SGT", "EQ", "ISZERO", "AND", "OR", "XOR",
                     "NOT", "BYTE"]