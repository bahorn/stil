# stil 

Just a rather boring stack machine implementation acting as an IL for a small
subset of python.

Can run with:
```
python3 src ./tests/a.py
```

Uses the `ast` module to iterate though the code, translating known parts to
the IL.

Currently just asignments, which might break because keeping track of the stack
hasn't been fully tested in every case.

## License

MIT
