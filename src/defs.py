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
