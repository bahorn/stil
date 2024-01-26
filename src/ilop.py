"""
Our IL operations
"""
import ast
from defs import IP, SP, Unimplemented


class ILOp:
    CONSUMES = 0
    OUTPUT = True

    def action(self, state):
        raise Unimplemented()

    def consumes(self):
        return self.CONSUMES

    def output(self):
        return self.OUTPUT

    def __str__(self):
        return self.__class__.__name__

    def concrete_x86(self):
        raise Unimplemented('x86-', self)


class NOP(ILOp):
    def action(self, state):
        pass


class DoneOp(ILOp):
    def action(self, state):
        state.done()


# Stack manipulation

class PushOp(ILOp):
    CONSUMES = -1

    def __init__(self, value):
        self._value = value

    def action(self, state):
        state.push(self._value)

    def __str__(self):
        return f'PushOp ({self._value})'


class PushZeroOp(ILOp):
    CONSUMES = -1

    def action(self, state):
        state.push(0)


class IncOp(ILOp):
    def action(self, state):
        a = state.pop()
        state.push(a + 1)


class PopOp(ILOp):
    CONSUMES = 1

    def action(self, state):
        state.pop()


class PeekOp(ILOp):
    def action(self, state):
        a = state.pop()
        b = state.peek(a)
        state.push(b)


class PokeOp(ILOp):
    CONSUMES = 2

    def action(self, state):
        a = state.pop()
        b = state.pop()
        state.poke(a, b)


class StageSPOp(ILOp):
    CONSUMES = 0

    def action(self, state):
        state.stage_stack_base(SP(len(state._stack)))


class SetSPOp(ILOp):
    CONSUMES = 0

    def action(self, state):
        state.set_stack_base()


class PushSPOp(ILOp):
    CONSUMES = -1

    def action(self, state):
        sp = state.get_stack_base()
        state.push(sp)


class PopSPOp(ILOp):
    CONSUMES = 1

    def action(self, state):
        sp = state.pop()
        state.stage_stack_base(sp)
        state.set_stack_base()


class DupOp(ILOp):
    CONSUMES = -1

    def action(self, state):
        state.push(state.peek())


class SwapOp(ILOp):
    def action(self, state):
        a = state.pop()
        b = state.pop()
        state.push(a)
        state.push(b)


# Normal operations

class SingleOp(ILOp):
    CONSUMES = 0

    def op(self, a):
        raise Unimplemented()

    def action(self, state):
        a = state.pop()
        state.push(self.op(a))


class NotOp(SingleOp):
    def op(self, a):
        return -a


class DoubleOp(ILOp):
    CONSUMES = 1

    def op(self, a, b):
        raise Unimplemented()

    def action(self, state):
        a = state.pop()
        b = state.pop()
        state.push(self.op(a, b))


class AddOp(DoubleOp):
    def op(self, a, b):
        if isinstance(b, IP):
            return IP(a + b)
        return a + b


class SubOp(DoubleOp):
    def op(self, a, b):
        return a - b


class MulOp(DoubleOp):
    def op(self, a, b):
        return a * b


class DivOp(DoubleOp):
    def op(self, a, b):
        return a / b


class XorOp(DoubleOp):
    def op(self, a, b):
        return a ^ b


class AndOp(DoubleOp):
    def op(self, a, b):
        return a & b


# Conditionals

class CmpOp(ILOp):
    CONSUMES = 2

    def cond(self, state):
        raise Unimplemented()

    def action(self, state):
        state.set_cond(self.cond(state))


class CmpEqOp(CmpOp):
    def cond(self, state):
        a = state.pop()
        b = state.pop()
        return a == b


class CmpNEqOp(CmpOp):
    def cond(self, state):
        a = state.pop()
        b = state.pop()
        return a != b


class CmpGEqOp(CmpOp):
    def cond(self, state):
        a = state.pop()
        b = state.pop()
        return a >= b


class CmpLEqOp(CmpOp):
    def cond(self, state):
        a = state.pop()
        b = state.pop()
        return a <= b


class CmpGTOp(CmpOp):
    def cond(self, state):
        a = state.pop()
        b = state.pop()
        return a > b


class CmpLTOp(CmpOp):
    def cond(self, state):
        a = state.pop()
        b = state.pop()
        return a < b


# Control Flow

class JumpOp(ILOp):
    CONSUMES = 1

    def cond(self, state):
        return True

    def action(self, state):
        ip = state.pop()
        if self.cond(state):
            state.set_ip(ip)
            return 0


class JumpCondOp(JumpOp):
    def cond(self, state):
        return state.get_cond()


class PushIpOp(ILOp):
    CONSUMES = -1

    def action(self, state):
        state.push(state.get_ip())


class PopIpOp(ILOp):
    CONSUMES = 1

    def action(self, state):
        next = state.pop()
        state.set_ip(next)


class InteruptOp(ILOp):
    CONSUMES = 2

    def action(self, state):
        interupt = state.pop()

        match interupt:
            case 1:
                print(f'> {state.pop()}')
            case _:
                raise Unimplemented()


class POp(ILOp):
    CONSUMES = 0

    def __init__(self, name):
        self._name = name

    def name(self):
        return self._name

    def __str__(self):
        return f'{self.__class__.__name__} ({self._name})'

    def consumes(self):
        return self.CONSUMES


class Info(POp):
    OUTPUT = False
    pass


class Label(POp):
    pass


class JumpPOp(POp):
    pass


class JumpCondPOp(JumpPOp):
    pass


class VariableLabel(POp):
    """
    Labels the stack position being inserted
    """
    OUTPUT = False


class PushPOp(POp):
    """
    A Pushop that refers to a stack position
    """
    CONSUMES = -1


class ResolvePOp(POp):
    def __init__(self, name, variable):
        self._name = name
        self._variable = variable

    def variable(self):
        return self._variable


class ResolvePokePOp(ResolvePOp):
    CONSUMES = 0


class ResolvePeekPOp(ResolvePOp):
    CONSUMES = 0


class PopArg(POp):
    """
    Balancing arguments we just removed when returning.
    """
    CONSUMES = -1


class PushArg(POp):
    """
    Balancing the value we pushed as the return value.
    """
    CONSUMES = 1
