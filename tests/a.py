from code_lib import entrypoint


def fun(k):
    y = k + 1
    return y


@entrypoint
def main():
    a = 3
    v = 10

    while v:
        a = fun(a) + 1
        v = v - 1

    return a
