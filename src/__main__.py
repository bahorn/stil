import ast
import sys

from interpreter import assemble_and_run_interpreter


def main():
    with open(sys.argv[1]) as f:
        code = f.read()

    # for idx, op in enumerate(ilins):
    #    print(f'{idx:04} {op}')

    assemble_and_run_interpreter(ast.parse(code))


if __name__ == "__main__":
    main()
