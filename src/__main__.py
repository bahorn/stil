"""
A stack machine and tooling to translate a small subset of python to it.
"""
import ast
import sys


class Unimplemented(Exception):
    pass


class Undefined(Exception):
    pass


class State:
    def __init__(self, instructions):
        self._stack = []
        self._instructions = instructions
        self._curr = 0
        self._cond = False
        self._done = False

    def peek(self, idx=1):
        return self._stack[-idx]

    def poke(self, idx, value):
        self._stack[-idx] = value

    def pop(self):
        res = self._stack[-1]
        self._stack = self._stack[:-1]
        return res

    def push(self, value):
        self._stack += [value]

    def step(self):
        if self._done:
            return

        try:
            ins = self._instructions[self._curr]
        except IndexError:
            self._done = True
            return

        print(f'{self._curr:04x} {ins}')

        next = ins.action(self)
        if next is None:
            next = 1
        self._curr += next

    def set_ip(self, value):
        self._curr = value

    def get_ip(self):
        return self._curr

    def set_cond(self, value):
        self._cond = value

    def get_cond(self):
        return self._cond

    def done(self):
        self._done = True

    def is_done(self):
        return self._done


class ILOp:
    CONSUMES = 0

    def action(self, state):
        raise Unimplemented()

    def consumes(self):
        return self.CONSUMES

    def __str__(self):
        return self.__class__.__name__


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
        # print(a, b)
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
        if self.cond(state):
            state.set_ip(state.pop())
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
        print(next)
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


class POp:
    def __init__(self, name):
        self._name = name

    def name(self):
        return self._name

    def __str__(self):
        return f'{self.__class__.__name__} ({self._name})'


class Info(POp):
    pass


class Label(POp):
    pass


class JumpPOp(POp):
    pass


class JumpCondPOp(JumpPOp):
    pass


def assemble(ins_list):
    new_ins_tmp = []
    new_ins = []
    labels = {}

    # two passes so all labels are resolved.

    idx = 0
    for ins in ins_list:
        if not isinstance(ins, POp):
            new_ins_tmp.append(ins)
            idx += 1
            continue

        match ins:
            case Label():
                labels[ins.name()] = idx
            case JumpPOp():
                # we are adding in two new instructions
                new_ins_tmp.append(ins)
                idx += 2
            case Info():
                continue
            case _:
                raise Unimplemented()

    for ins in new_ins_tmp:
        if not isinstance(ins, JumpPOp):
            new_ins.append(ins)
            continue

        # target
        new_ins.append(PushOp(labels[ins.name()]))

        if isinstance(ins, JumpCondPOp):
            new_ins.append(JumpCondOp())
        else:
            new_ins.append(JumpOp())

    return new_ins


# Now Functions that can be used for the translation

class TranslationNamespace:
    def __init__(self):
        self._stack = []
        self._offset = 0
        self.enter('global')

    def enter(self, name=None):
        self._stack += [{
            'name': name,
            'offsets': {},
            'base': self._offset
        }]

    def leave(self):
        self._offset = self._stack[-1]['base']
        self._stack = self._stack[:-1]

    def define(self, symbol):
        print(self._offset, symbol)
        curr = self._stack[-1]['offsets']
        curr[symbol] = self._offset - self._stack[-1]['base']

    def depth(self):
        return self._offset - self._stack[-1]['base']

    def push(self, count=1):
        # just a push that we had nothing to do with.
        print('> push')
        self._offset += count

    def pop(self, count=1):
        print('> pop')
        self._offset -= count

    def offset(self, symbol):
        """
        Find the relative offset from the current position for the instruction.
        """
        res = None

        for frame in self._stack[::-1]:
            if symbol in frame['offsets']:
                sym = frame['offsets'][symbol]
                print(sym, self._offset, frame['base'])
                return self._offset - (frame['base'] + sym)

        return res


class Translator(ast.NodeVisitor):
    def __init__(self):
        self._ts = TranslationNamespace()
        self._funcs = {}
        self._res = []
        self._curr = None
        self._entrypoint = None

    def result(self):
        res = []
        for func, body in self._funcs.items():
            if func == self._entrypoint:
                continue
            res += body
        res = self._funcs[self._entrypoint] + res
        return res

    def generic_visit(self, node):
        super().generic_visit(node)

    def visit_Constant(self, node):
        self._ts.push()
        self._res.append(PushOp(node.value))

    def visit_Name(self, node):
        self._ts.push()
        off = self._ts.offset(node.id)
        self._res.append(PushOp(off))
        self._res.append(PeekOp())
        self._ts.pop()

    def visit_Assign(self, node):
        # check if it already exists in the namespace.
        if len(node.targets) != 1:
            raise Unimplemented()

        target = node.targets[0].id
        self._res.append(Info(f'Assign {target}'))

        offset = self._ts.offset(target)

        # The value will be pushed to the stack
        self.visit(node.value)

        if offset is None:
            self._ts.define(target)
        else:
            offset = self._ts.offset(target)
            self._res.append(PushOp(offset))
            self._res.append(PokeOp())
            self._ts.pop()

    def visit_AugAssign(self, node):
        raise Unimplemented()

    def visit_AnnAssign(self, node):
        raise Unimplemented()

    def visit_Name(self, node):
        self._ts.push()
        res = self._ts.offset(node.id)
        self._res.append(PushOp(res))
        self._res.append(PeekOp())

    def visit_expr(self, node):
        self.generic_visit(node)

    def visit_BinOp(self, node):
        self.generic_visit(node)
        op = None

        match node.op:
            case ast.Add():
                op = AddOp()
            case ast.Sub():
                op = SubOp()
            case ast.Mult():
                op = MulOp()
            case ast.Div():
                op = DivOp()
            case _:
                raise Unimplemented()
        self._res.append(op)
        self._ts.pop(op.consumes())

    def visit_Call(self, node):
        self._res.append(Info(f'call {node.func.id}'))
        if node.func.id == 'print':
            for arg in node.args:
                self.visit(arg)
            self._res.append(PushOp(1))
            self._res.append(InteruptOp())
            # restore the stack
            for arg in node.args:
                self._ts.pop()
            return

        # self.generic_visit(node)
        self._res.append(PushIpOp())
        self._res.append(PushOp(4))
        self._res.append(AddOp())
        self._res.append(JumpPOp(node.func.id))
        self._ts.push()

    def visit_Return(self, node):
        self._res.append(Info(f'Return {ast.unparse(node.value)}'))
        if self._curr == self._entrypoint:
            self._res.append(DoneOp())
            return

        self.generic_visit(node)
        # need to restore the stack back to its original value
        for _ in range(self._ts.depth() - 1):
            self._res.append(SwapOp())
            self._res.append(PopOp())
        # now restore the IP and jump
        self._res.append(SwapOp())
        self._res.append(PopIpOp())

    def visit_While(self, node):
        self._res.append(Info(f'While {node}'))
        raise Unimplemented()

    def visit_If(self, node):
        self._res.append(Info(f'If {node}'))
        raise Unimplemented()

    def visit_FunctionDef(self, node):
        self._funcs[node.name] = []
        self._curr = node.name

        self._ts.enter(node.name)
        for decorator in node.decorator_list:
            if decorator.id == 'entrypoint':
                self._entrypoint = node.name

        self._res.append(Info(f'Function {node.name}'))
        self._res.append(Label(node.name))
        # deal with the arguments
        for child in node.body:
            self.visit(child)
        # print(node.__dict__)
        self._funcs[node.name] = self._res
        self._res = []
        self._ts.leave()

    def visit_Module(self, node):
        # self._res.append(Info(f'Module {node}'))
        self.generic_visit(node)


# Main

def main():
    t = Translator()
    with open(sys.argv[1]) as f:
        code = f.read()
    t.visit(ast.parse(code))
    ins = t.result()
    for idx, op in enumerate(ins):
        print(f'{idx:04x} {op}')

    print()
    s = State(assemble(ins))
    while not s.is_done():
        print(s._stack)
        s.step()


if __name__ == "__main__":
    main()
