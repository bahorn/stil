from code_lib import entrypoint


def fun2():
    k = 4
    return k


def fun():
    x = fun2()
    y = 52 * x
    return y


@entrypoint
def main():
    a = 3
    b = 10
    a = a + b + 2
    a = a + fun()
    print(a)
    return 1
