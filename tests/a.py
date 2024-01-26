from code_lib import entrypoint

"""
def fun2(a, b):
    c = a + b
    d = c + 5
    return c


def fun(k):
    y = fun2(k, 10)
    return y


@entrypoint
def main():
    a = 2
    d = fun(5)
    return a + d

"""

@entrypoint
def main():
    a = 3
    c = 1
    if c:
        a = a + 4
    b = 5
    return a + b
