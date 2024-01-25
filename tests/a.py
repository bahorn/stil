from code_lib import entrypoint


def fun3(v):
    return v - 1


def fun2():
    return 2 + fun3(3)


def fun(k):
    return 42 + k + fun2() + fun2()


@entrypoint
def main():
    a = 3
    d = fun(10)
    a = a + d
    return a
