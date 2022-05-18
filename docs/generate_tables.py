from pathlib import Path

import click

from disco.exceptions import EXCEPTIONS_TO_ERROR_CODES


@click.command()
@click.argument("output-dir", callback=lambda _, __, x: Path(x))
def generate_tables(output_dir):
    output_dir.mkdir(exist_ok=True, parents=True)
    generate_return_codes(output_dir)


def generate_return_codes(output_dir):
    output_file = output_dir / "return_codes.csv"
    with open(output_file, "w") as f_out:
        header = "Return Code,Description"
        f_out.write("\t".join(header) + "\n")
        f_out.write("0,Success\n")
        f_out.write("1,Generic error\n")
        for item in EXCEPTIONS_TO_ERROR_CODES.values():
            f_out.write(str(item["error_code"]))
            f_out.write(",")
            f_out.write(item["description"])
            f_out.write("\n")
    

if __name__ == "__main__":
    generate_tables()
