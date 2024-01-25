from code_lib import entrypoint


def fun2(a, b):
    c = a + b
    return c + 2


def fun(k):
    v = k + 99
    v = v + 1
    return v


@entrypoint
def main():
    a = 2
    d = fun(5)
    a = a * d
    d = fun2(10, 10)
    return a + d
