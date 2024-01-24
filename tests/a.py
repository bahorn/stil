from code_lib import entrypoint


@entrypoint
def main():
    a = 3
    b = 9
    print(a)
    c = a + 1
    d = a + 2
    e = a + 3
    h = a + b
    a = h + 3
    b = 2
    print(a)
    return 1
