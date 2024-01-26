# stil 

Just a rather boring stack machine implementation acting as an IL for a small
subset of python.

Can run with:
```
python3 src ./tests/a.py
```

Uses the `ast` module to iterate though the code, translating known parts to
the IL.

Currently has support for:
* function calls, with arguments
* assignments
* the usual set of binops
* while loops
* if statements

Some quirks:
* Only an int type is supported
* If statements are only true if the condition is equal to 1
* While loops continue until the condition is equal to 0

See the `tests/a.py` file for sample code that it supports.

Probably has bugs!

## License

MIT
