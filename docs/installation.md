# Installation

## Requirements

- Python 3.10 or newer
- An NCAA Football 14 dynasty save on RPCS3 (or an extracted `USR-DATA` binary)

## Installing with pip

Install the package directly using `pip`:

```bash
pip install ncaa-dynasty-rerank
```

To install from source:

```bash
git clone https://github.com/matthewkdies/ncaa-dynasty-rerank.git
cd ncaa-dynasty-rerank
pip install .
```

## Installing with uv

If you use `uv`:

```bash
uv tool install ncaa-dynasty-rerank
```

Or run directly without installation:

```bash
uvx --from . ncaa-dynasty-rerank --help
```

## Verifying Installation

Verify that the CLI executable is available on your PATH:

```bash
ncaa-dynasty-rerank --help
```

## Dependencies

The package has two runtime dependencies:

- `pydantic >= 2.0.0`: Used for configuration models, validation, and serialization.
- `rich >= 13.0.0`: Used for terminal output, tables, and syntax formatting.
