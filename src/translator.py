import ast

import ilop
from defs import SP, IP


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
        ast.BinOp, ast.If, ast.While
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
        self._res.append(ilop.PushPOp(ref))
        # 2
        self._res.append(ilop.PokeOp())
        self._res.append(ilop.ResolvePokePOp(ref, target))

    def visit_Call(self, node):
        # -2 to remove the ip and sp
        call_args = len(self._remap[node.func.id]['args']) - 1
        if len(node.args) != call_args:
            raise Exception("Arg missmatch!")

        # Layout:
        # SP [arg1 ... argn] IP

        # Push the current SP to the stack
        self._res.append(ilop.PushSPOp())

        # so we need to keep the sp while evaluating arguments, as they need to
        # refer to the current state.
        # but want it to be set at this point as we need the index
        self._res.append(ilop.StageSPOp())

        # push all the arguments onto the stack
        for arg in node.args:
            self.visit(arg)

        self._res.append(ilop.SetSPOp())

        # push the return address to the stack
        self._res.append(ilop.PushIpOp())
        # the code after is 4 operations ahead of the ip of that PushIpOp()
        self._res.append(ilop.PushOp(4))
        self._res.append(ilop.AddOp())

        self._res.append(ilop.JumpPOp(node.func.id))
        # Back in our code, we want to pop the arguments
        for _ in node.args:
            # Swaping to preserve the return value
            self._res.append(ilop.SwapOp())
            self._res.append(ilop.PopOp())

        self._res.append(ilop.SwapOp())
        self._res.append(ilop.PopSPOp())

    def visit_Name(self, node):
        ref = self.get_idx(node.id)
        self._res.append(ilop.PushPOp(ref))
        self._res.append(ilop.PeekOp())
        self._res.append(ilop.ResolvePeekPOp(ref, node.id))

    def visit_Constant(self, node):
        # -1
        op = ilop.PushOp(node.value)
        self._res.append(op)

    def visit_Return(self, node):
        # duplicate the return value
        self._res.append(ilop.PushArg('ret'))
        self.visit(node.value)

        # pop our local state off, leaving just the return arguments.
        for var in self._remap[self._funcname]['defs']:
            self._res.append(ilop.PopArg(var))
            self._res.append(ilop.SwapOp())
            self._res.append(ilop.PopOp())

        # now restore the IP and jump
        self._res.append(ilop.PopArg('ip'))
        self._res.append(ilop.SwapOp())
        self._res.append(ilop.PopIpOp())

    def visit_Expr(self, node):
        # just a wrapper around things we care about
        self.generic_visit(node)

    def visit_BinOp(self, node):
        op = None
        self.visit(node.right)
        self.visit(node.left)

        match node.op:
            case ast.Add():
                op = ilop.AddOp()
            case ast.Sub():
                op = ilop.SubOp()
            case ast.Mult():
                op = ilop.MulOp()
            case ast.Div():
                op = ilop.DivOp()
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
        self._res.append(ilop.PushOp(1))
        self._res.append(ilop.CmpNEqOp())
        self._res.append(ilop.JumpCondPOp(ref))

        # body
        for item in node.body:
            self.visit(item)

        # Fall through label
        self._res.append(ilop.Label(ref))
        self._res.append(ilop.NOP())

    def visit_While(self, node):
        if node.orelse != []:
            raise Unimplemented()

        ref_cond = self.get_idx('while-cond')
        ref_end = self.get_idx('while-end')

        # Conditional Check
        self._res.append(ilop.Label(ref_cond))
        self.visit(node.test)
        # if it fails, jump to ref
        self._res.append(ilop.PushOp(0))
        self._res.append(ilop.CmpEqOp())
        self._res.append(ilop.JumpCondPOp(ref_end))

        # body
        for item in node.body:
            self.visit(item)

        self._res.append(ilop.JumpPOp(ref_cond))

        # Fall through label
        self._res.append(ilop.Label(ref_end))
        self._res.append(ilop.NOP())


def resolve_statement(statement, fun, remap):
    depth = 0

    new = []
    resolved = {}

    for op in statement:
        depth -= op.consumes()
        if not isinstance(op, ilop.ResolvePOp):
            continue

        if op.name() in resolved:
            assert Exception()

        offset = remap[fun]['idx'][op.variable()]
        match op:
            case ilop.ResolvePokePOp():
                resolved[op.name()] = offset
            case ilop.ResolvePeekPOp():
                resolved[op.name()] = offset
            case _:
                continue

    for op in statement:
        if isinstance(op, ilop.ResolvePOp):
            continue

        if not isinstance(op, ilop.PushPOp):
            new.append(op)
            continue

        res = resolved[op.name()]
        new.append(ilop.PushOp(res))

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
        res.append(ilop.VariableLabel(var))
        res.append(ilop.PushZeroOp())

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
        res.append(ilop.Info(f'Function {fun}'))
        res.append(ilop.Label(fun))
        res += code

    # Finally, add in a _start method that will call the entrypoint
    # Calls the entrypoint with no arguments, so it can return to a DoneOp
    # JumpPOp assembles to 2 instructions, giving the offset.
    _start = [
        ilop.Info('_start'),
        ilop.Label('_start'),
        ilop.PushSPOp(),
        ilop.StageSPOp(),
        ilop.SetSPOp(),
        ilop.PushOp(IP(5)),
        ilop.JumpPOp(entrypoint),
        ilop.SwapOp(),
        ilop.PopOp(),
        ilop.DoneOp()
    ]

    return _start + res
