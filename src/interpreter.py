"""
A stack machine and tooling to translate a small subset of python to it.
"""
import ilop
from translator import il_translation
from defs import IP, SP, Unimplemented


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
        print(value, isinstance(value, IP))
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


def assemble_interpreter(ins_list):
    new_ins_tmp = []
    new_ins = []
    labels = {}

    # two passes so all labels are resolved.

    idx = 0
    for ins in ins_list:
        if not isinstance(ins, ilop.POp):
            new_ins_tmp.append(ins)
            idx += 1
            continue

        match ins:
            case ilop.Label():
                labels[ins.name()] = idx
            case ilop.JumpPOp():
                # this will handle the JumpCondPOp, as that is inheriting from
                # it.
                # we are adding in two new instructions
                new_ins_tmp.append(ins)
                idx += 2
            case ilop.Info():
                continue
            case ilop.VariableLabel():
                continue
            case ilop.PopArg():
                continue
            case ilop.PushArg():
                continue
            case _:
                raise Unimplemented(ins)

    for ins in new_ins_tmp:
        if not isinstance(ins, ilop.JumpPOp):
            new_ins.append(ins)
            continue

        # target
        new_ins.append(ilop.PushOp(IP(labels[ins.name()])))

        if isinstance(ins, ilop.JumpCondPOp):
            new_ins.append(ilop.JumpCondOp())
        else:
            new_ins.append(ilop.JumpOp())

    return new_ins


# Main

def assemble_and_run_interpreter(code):
    ins = il_translation(code)
    ilins = assemble_interpreter(ins)
    s = State(ilins, maxins=1000)
    print()
    while not s.is_done():
        s.step()
