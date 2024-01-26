"""
A stack machine and tooling to translate a small subset of python to it.
"""
import ast
import sys


class Unimplemented(Exception):
    pass


class Undefined(Exception):
    pass


class SP(int):
    def __str__(self):
        return f'SP({super().__str__()})'


class IP(int):
    def __str__(self):
        return f'IP({super().__str__()})'


class State:
    def __init__(self, instructions, maxins=100):
        self._stack = []
        self._instructions = instructions
        self._curr = 0
        self._cond = False
        self._done = False
        self._stack_base = SP(0)
        self._stack_base_stage = SP(0)
        self._maxins = maxins
        self._ins = 0

    def peek(self, idx=0):
        assert idx >= 0
        return self._stack[self._stack_base + idx]

    def poke(self, idx, value):
        assert idx >= 0
        self._stack[self._stack_base + idx] = value

    def pop(self):
        res = self._stack[-1]
        self._stack = self._stack[:-1]
        return res

    def push(self, value):
        self._stack += [value]

    def step(self):
        if self._ins >= self._maxins:
            self.done()
            return

        if self._done:
            return

        try:
            ins = self._instructions[self._curr]
        except IndexError:
            self._done = True
            return

        print(f'INS: {self._curr:04} {ins}')
        print(f'STB: {self._stack_base}')
        print('STF:', ' '.join(map(lambda x: f'{x[1]}', enumerate(self._stack))))
        print()

        next = ins.action(self)
        if next is None:
            next = 1
        self._curr += next

        self._ins += 1

    def set_ip(self, value):
        assert isinstance(value, IP)
        self._curr = value

    def get_ip(self):
        return IP(self._curr)

    def set_cond(self, value):
        self._cond = value

    def get_cond(self):
        return self._cond

    def set_stack_base(self):
        self._stack_base = self._stack_base_stage

    def stage_stack_base(self, value):
        assert isinstance(value, SP)
        self._stack_base_stage = value

    def get_stack_base(self):
        return self._stack_base

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


class POp:
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
            case VariableLabel():
                continue
            case PopArg():
                continue
            case PushArg():
                continue
            case _:
                raise Unimplemented(ins)

    for ins in new_ins_tmp:
        if not isinstance(ins, JumpPOp):
            new_ins.append(ins)
            continue

        # target
        new_ins.append(PushOp(IP(labels[ins.name()])))

        if isinstance(ins, JumpCondPOp):
            new_ins.append(JumpCondOp())
        else:
            new_ins.append(JumpOp())

    return new_ins


# Now Functions that can be used for the translation


class VariableDefinitions(ast.NodeVisitor):
    """
    Pass to discover all variable definitions in the ast.

    Does not resolve the actual assignment value, just for name discovery.
    """

    def __init__(self):
        self._funcs = {}
        self._definitions = []
        self._curr = None

    def results(self):
        return self._funcs

    def visit_Assign(self, node):
        if len(node.targets) != 1:
            raise Unimplemented()

        target = node.targets[0].id
        self._definitions.append(target)

    def visit_FunctionDef(self, node):
        self._curr = node.name
        self.generic_visit(node)

        decorators = [decorator.id for decorator in node.decorator_list]

        # ip is an hidden argument, used as part of the calling convention
        self._funcs[self._curr] = {
            'args': [arg.arg for arg in node.args.args] + ['_ip'],
            'defs': sorted(list(set(self._definitions))),
            'ref': node,
            'decorators': decorators,
        }
        self._internal = []
        self._curr = None


class StatementTranslator(ast.NodeVisitor):
    """
    Translates a statement in a function body.

    Statements should always return the stack back to its original state.
    (with the exception of return statements, which are handled by inserting
     balancing arguments)

    The only things that should be pushing new values to the stack that stay
    are entering functions.
    """

    IMPLEMENTED = (
        ast.Assign, ast.Call, ast.Return, ast.Name, ast.Constant, ast.Expr,
        ast.BinOp
    )

    def __init__(self, funcname, remap):
        self._res = []
        self._idx = 0
        self._remap = remap
        self._funcname = funcname

    def results(self):
        return self._res

    def get_idx(self, name):
        self._idx += 1
        return f'{name}-{self._idx}'

    def generic_visit(self, node):
        if not isinstance(node, self.IMPLEMENTED):
            raise Unimplemented(node)

        super().generic_visit(node)

    def visit_Assign(self, node):
        target = node.targets[0].id
        ref = self.get_idx(target)

        self.visit(node.value)
        # -1
        self._res.append(PushPOp(ref))
        # 2
        self._res.append(PokeOp())
        self._res.append(ResolvePokePOp(ref, target))

    def visit_Call(self, node):
        # -2 to remove the ip and sp
        call_args = len(self._remap[node.func.id]['args']) - 1
        if len(node.args) != call_args:
            raise Exception("Arg missmatch!")

        # Layout:
        # SP [arg1 ... argn] IP

        # Push the current SP to the stack
        self._res.append(PushSPOp())

        # so we need to keep the sp while evaluating arguments, as they need to
        # refer to the current state.
        # but want it to be set at this point as we need the index
        self._res.append(StageSPOp())

        # push all the arguments onto the stack
        for arg in node.args:
            self.visit(arg)

        self._res.append(SetSPOp())

        # push the return address to the stack
        self._res.append(PushIpOp())
        # the code after is 4 operations ahead of the ip of that PushIpOp()
        self._res.append(PushOp(4))
        self._res.append(AddOp())

        self._res.append(JumpPOp(node.func.id))
        # Back in our code, we want to pop the arguments
        for _ in node.args:
            # Swaping to preserve the return value
            self._res.append(SwapOp())
            self._res.append(PopOp())

        self._res.append(SwapOp())
        self._res.append(PopSPOp())

    def visit_Name(self, node):
        ref = self.get_idx(node.id)
        self._res.append(PushPOp(ref))
        self._res.append(PeekOp())
        self._res.append(ResolvePeekPOp(ref, node.id))

    def visit_Constant(self, node):
        # -1
        op = PushOp(node.value)
        self._res.append(op)

    def visit_Return(self, node):
        # duplicate the return value
        self._res.append(PushArg('ret'))
        self.visit(node.value)

        # pop our local state off, leaving just the return arguments.
        for var in self._remap[self._funcname]['defs']:
            self._res.append(PopArg(var))
            self._res.append(SwapOp())
            self._res.append(PopOp())

        # now restore the IP and jump
        self._res.append(PopArg('ip'))
        self._res.append(SwapOp())
        self._res.append(PopIpOp())

    def visit_Expr(self, node):
        # just a wrapper around things we care about
        self.generic_visit(node)

    def visit_BinOp(self, node):
        op = None
        self.visit(node.right)
        self.visit(node.left)

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

    def visit_If(self, node):
        if node.orelse != []:
            raise Unimplemented()

        ref = self.get_idx('if')
        # Conditional Check
        self.visit(node.test)
        # if it fails, jump to ref
        self._res.append(PushOp(1))
        self._res.append(CmpNEqOp())
        self._res.append(JumpCondPOp(ref))

        # body
        for item in node.body:
            self.visit(item)

        # Fall through label
        self._res.append(Label(ref))
        self._res.append(NOP())


def resolve_statement(statement, fun, remap):
    depth = 0

    new = []
    resolved = {}

    for op in statement:
        depth -= op.consumes()
        if not isinstance(op, ResolvePOp):
            continue

        if op.name() in resolved:
            assert Exception()

        offset = remap[fun]['idx'][op.variable()]
        match op:
            case ResolvePokePOp():
                resolved[op.name()] = offset
            case ResolvePeekPOp():
                resolved[op.name()] = offset
            case _:
                continue

    for op in statement:
        if isinstance(op, ResolvePOp):
            continue

        if not isinstance(op, PushPOp):
            new.append(op)
            continue

        res = resolved[op.name()]
        new.append(PushOp(res))

    assert depth == 0
    return new


def fun_translation(fun, remapped):
    """
    Translate this function
    """
    ref = remapped[fun]
    res = []

    # initialize all the internal variables as zero
    for var in ref['defs']:
        res.append(VariableLabel(var))
        res.append(PushZeroOp())

    # we can now start translating the code, statement by statement.
    for expr in ref['ref'].body:
        st = StatementTranslator(fun, remapped)
        st.visit(expr)
        translated = st.results()
        # If we generate uneven code, we have an issue.
        # For things like return, we have statements inserted to do the
        # balancing
        assert sum([op.consumes() for op in translated]) == 0
        # Now fix up the references to variables
        res += resolve_statement(translated, fun, remapped)

    return res


def il_translation(code):
    # First, we need a list of variables and arguments for each function
    vd = VariableDefinitions()
    vd.visit(code)
    # Next, map these to offsets in the current function
    remapped = {}

    entrypoint = None

    for fun, vars in vd.results().items():
        defs = vars['defs']
        args = vars['args']
        res = {i: idx for idx, i in enumerate(args + defs)}
        print(res)
        remapped[fun] = vars.copy()
        remapped[fun]['idx'] = res

        print(fun, res)

        if 'entrypoint' in vars['decorators']:
            entrypoint = fun

    translated = {}

    # Do the translation, that still has some symbolic operations
    for fun, _ in remapped.items():
        translated[fun] = fun_translation(fun, remapped)

    # Now merge the code together
    res = []
    for fun, code in translated.items():
        res.append(Info(f'Function {fun}'))
        res.append(Label(fun))
        res += code

    # Finally, add in a _start method that will call the entrypoint
    # Calls the entrypoint with no arguments, so it can return to a DoneOp
    # JumpPOp assembles to 2 instructions, giving the offset.
    _start = [
        Info('_start'),
        Label('_start'),
        PushSPOp(),
        StageSPOp(),
        SetSPOp(),
        PushOp(IP(5)),
        JumpPOp(entrypoint),
        SwapOp(),
        PopOp(),
        DoneOp()
    ]

    return _start + res


# Main

def main():
    with open(sys.argv[1]) as f:
        code = f.read()

    ins = il_translation(ast.parse(code))

    ilins = assemble(ins)

    for idx, op in enumerate(ilins):
        print(f'{idx:04} {op}')

    print()
    import time
    s = State(assemble(ins), maxins=400)
    while not s.is_done():
        s.step()


if __name__ == "__main__":
    main()
